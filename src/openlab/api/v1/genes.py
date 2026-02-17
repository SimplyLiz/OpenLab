"""Gene API endpoints."""

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File, Query
from sqlalchemy.orm import Session

from openlab.api.deps import get_db
from openlab.api.v1.schemas import (
    ApproveRequest,
    ConvergenceResponse,
    CorrectRequest,
    DisagreementPairOut,
    DisagreementResponse,
    EvidenceOut,
    GeneListItem, GeneDetail, GeneDossier, GenomeStatusResponse, GraduateRequest, HypothesisDetail, ImportResult,
    ResearchQueueItem,
    ResearchStatus,
    ResearchSummary,
)
from openlab.db.models.gene import Gene
from openlab.exceptions import HypothesisNotFoundError
from openlab.services import gene_service, hypothesis_service, import_service

router = APIRouter(prefix="/genes", tags=["genes"])


# ── Genome hydration endpoints (must precede /{gene_id} routes) ───────


@router.get("/genome/status", response_model=GenomeStatusResponse)
def genome_status(db: Session = Depends(get_db)):
    """Quick check: does the DB have genes?"""
    count = db.query(Gene).count()
    return GenomeStatusResponse(has_genome=count > 0, gene_count=count)


@router.get("/genome/hydrate")
def genome_hydrate(db: Session = Depends(get_db)):
    """Reconstruct a full GenomeRecord from DB rows.

    Rebuilds the same shape the pipeline produces so the frontend
    can hydrate without re-running genome_ingest. Now reads genome
    metadata from the Genome table instead of hardcoded values.
    """
    from openlab.models import FunctionalCategory, GenomeGene, GenomeRecord
    from openlab.services.genbank import _classify_gene, CATEGORY_COLORS
    from openlab.services.prior_knowledge import lookup
    from openlab.db.models.hypothesis import Hypothesis
    from openlab.db.models.genome import Genome

    # Look up the genome from the table (use the first one as default)
    genome_row = db.query(Genome).first()

    genes = db.query(Gene).order_by(Gene.start).all()
    if not genes:
        raise HTTPException(status_code=404, detail="No genes in database")

    # Pre-load best hypothesis per gene (single query)
    hyp_rows = (
        db.query(Hypothesis)
        .filter(Hypothesis.gene_id.isnot(None))
        .order_by(Hypothesis.confidence_score.desc())
        .all()
    )
    best_hyp: dict[int, Hypothesis] = {}
    for h in hyp_rows:
        if h.gene_id not in best_hyp:
            best_hyp[h.gene_id] = h

    genome_genes: list[GenomeGene] = []
    for g in genes:
        # 1. Graduated → green
        if g.graduated_at is not None:
            category = FunctionalCategory.PREDICTED
            color = "#34d399"
            source = "genelife"
        # 2. Has hypothesis from analysis pipeline → classify from predicted function
        elif g.gene_id in best_hyp:
            hyp = best_hyp[g.gene_id]
            proposed_fn = gene_service.extract_proposed_function(hyp)
            category, _ = _classify_gene(proposed_fn, g.name or "")
            if category == FunctionalCategory.UNKNOWN:
                category = FunctionalCategory.PREDICTED
            color = CATEGORY_COLORS.get(category, "#fb923c")
            source = "genelife"
        else:
            # 3. Prior knowledge (DNASyn / curated)
            prior = lookup(g.locus_tag)
            if prior:
                category = FunctionalCategory.PREDICTED
                color = "#fb923c"
                source = "dnasyn" if "dnasyn" in prior.source else "curated"
            else:
                # 4. Classify from product/name (same as genbank parser)
                category, _is_hypo = _classify_gene(g.product or "", g.name or "")
                color = CATEGORY_COLORS.get(category, "#888888")
                source = "genbank" if category != FunctionalCategory.UNKNOWN else ""

        genome_genes.append(GenomeGene(
            locus_tag=g.locus_tag,
            product=g.product or "",
            gene_name=g.name or "",
            start=g.start,
            end=g.end,
            strand=g.strand,
            dna_sequence=g.sequence or "",
            protein_sequence=g.protein_sequence or "",
            protein_length=len(g.protein_sequence or ""),
            functional_category=category,
            is_hypothetical=(category == FunctionalCategory.UNKNOWN),
            color=color,
            prediction_source=source,
        ))

    total = len(genome_genes)
    known = sum(1 for g in genome_genes if g.functional_category not in (
        FunctionalCategory.UNKNOWN, FunctionalCategory.PREDICTED
    ))
    predicted = sum(1 for g in genome_genes if g.functional_category == FunctionalCategory.PREDICTED)
    unknown = sum(1 for g in genome_genes if g.functional_category == FunctionalCategory.UNKNOWN)

    # Read genome metadata from table, fall back to Syn3A defaults
    record = GenomeRecord(
        accession=genome_row.accession if genome_row else "CP016816.2",
        organism=genome_row.organism if genome_row else "Synthetic Mycoplasma mycoides JCVI-syn3A",
        description=genome_row.description if genome_row else "Minimal synthetic bacterial genome JCVI-syn3A",
        genome_length=genome_row.genome_length if genome_row else 543379,
        is_circular=genome_row.is_circular if genome_row else True,
        gc_content=genome_row.gc_content if genome_row else 24.0,
        genes=genome_genes,
        total_genes=total,
        genes_known=known,
        genes_predicted=predicted,
        genes_unknown=unknown,
    )

    return record.model_dump()


@router.get("/research/queue", response_model=list[ResearchQueueItem])
def research_queue(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    """Return genes needing deep analysis, ordered by priority.

    Priority 0 = unknown genes with zero evidence (most urgent).
    Priority 1 = genes with stale evidence.
    """
    items: list[ResearchQueueItem] = []

    # Priority 0: unknown genes with zero evidence
    no_evidence = gene_service.genes_without_evidence(db)
    for i, g in enumerate(no_evidence):
        if len(items) >= limit:
            break
        items.append(ResearchQueueItem(
            locus_tag=g.locus_tag,
            gene_name=g.name,
            product=g.product,
            protein_sequence=g.protein_sequence,
            priority=0,
        ))

    # Priority 1: genes with stale evidence
    if len(items) < limit:
        stale = gene_service.genes_with_stale_evidence(db)
        for g in stale:
            if len(items) >= limit:
                break
            # Skip if already in the list
            if any(item.locus_tag == g.locus_tag for item in items):
                continue
            items.append(ResearchQueueItem(
                locus_tag=g.locus_tag,
                gene_name=g.name,
                product=g.product,
                protein_sequence=g.protein_sequence,
                priority=1,
            ))

    return items


@router.post("/import", response_model=ImportResult)
def import_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload and import a GenBank or FASTA file."""
    suffix = Path(file.filename or "").suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file.file.read())
        tmp_path = Path(tmp.name)

    try:
        if suffix in (".gb", ".gbk", ".genbank"):
            result = import_service.import_genbank(db, tmp_path)
        elif suffix in (".fasta", ".fa", ".fna"):
            result = import_service.import_fasta(db, tmp_path)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown file format: {suffix}")
        return result
    finally:
        tmp_path.unlink(missing_ok=True)


@router.get("", response_model=list[GeneListItem])
def list_genes(
    unknown_only: bool = Query(False),
    limit: int = Query(500, le=5000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List genes, optionally filtering to unknown-function only."""
    return gene_service.list_genes(db, unknown_only=unknown_only, limit=limit, offset=offset)


@router.get("/{gene_id}", response_model=GeneDetail)
def get_gene(gene_id: int, db: Session = Depends(get_db)):
    """Get a gene by ID with features and evidence."""
    return gene_service.get_gene(db, gene_id)


@router.get("/{gene_id}/dossier", response_model=GeneDossier)
def get_dossier(gene_id: int, db: Session = Depends(get_db)):
    """Get a full evidence dossier for a gene."""
    return gene_service.get_dossier(db, gene_id)


@router.get("/{gene_id}/hypothesis", response_model=HypothesisDetail | None)
def get_gene_hypothesis(gene_id: int, db: Session = Depends(get_db)):
    """Get the hypothesis for a specific gene."""
    hyp = hypothesis_service.get_hypothesis_for_gene(db, gene_id)
    if not hyp:
        raise HTTPException(status_code=404, detail="No hypothesis for this gene")
    return hyp


@router.get("/{gene_id}/convergence", response_model=ConvergenceResponse)
def get_gene_convergence(gene_id: int, db: Session = Depends(get_db)):
    """Compute convergence score for a gene's evidence."""
    from openlab.db.models.evidence import Evidence

    gene_service.get_gene(db, gene_id)
    score = gene_service.compute_convergence_score(db, gene_id)
    ev_count = db.query(Evidence).filter(Evidence.gene_id == gene_id).count()
    report = gene_service.detect_disagreements(db, gene_id)
    return ConvergenceResponse(
        gene_id=gene_id,
        convergence_score=score,
        evidence_count=ev_count,
        disagreement_count=len(report.disagreeing_pairs),
    )


@router.get("/{gene_id}/disagreements", response_model=DisagreementResponse)
def get_gene_disagreements(gene_id: int, db: Session = Depends(get_db)):
    """Detect disagreements between evidence sources for a gene."""
    gene_service.get_gene(db, gene_id)
    report = gene_service.detect_disagreements(db, gene_id)
    return DisagreementResponse(
        gene_id=gene_id,
        convergence_score=report.convergence_score,
        total_pairs=report.total_pairs,
        disagreeing_pairs=[
            DisagreementPairOut(
                evidence_id_a=dp.evidence_id_a,
                evidence_id_b=dp.evidence_id_b,
                source_a=dp.source_a,
                source_b=dp.source_b,
                evidence_type_a=dp.evidence_type_a,
                evidence_type_b=dp.evidence_type_b,
                agreement_score=dp.agreement_score,
                categories_a=sorted(dp.categories_a),
                categories_b=sorted(dp.categories_b),
            )
            for dp in report.disagreeing_pairs
        ],
    )


@router.patch("/{gene_id}/graduate", response_model=GeneDetail)
def graduate_gene(gene_id: int, body: GraduateRequest, db: Session = Depends(get_db)):
    """Graduate a gene — assign a proposed function."""
    try:
        gene = gene_service.graduate_gene(
            db, gene_id, body.proposed_function, hypothesis_id=body.hypothesis_id
        )
    except HypothesisNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return gene


@router.delete("/{gene_id}/graduate", status_code=204)
def ungraduate_gene(gene_id: int, db: Session = Depends(get_db)):
    """Reverse graduation — return gene to unknown pool."""
    try:
        gene_service.ungraduate_gene(db, gene_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return Response(status_code=204)


# ── Locus-tag based research endpoints ──────────────────────────────


def _convergence_tier(score: float) -> int:
    """Map convergence score to confidence tier (1=high .. 4=flagged)."""
    if score >= 0.7:
        return 1
    if score >= 0.4:
        return 2
    if score >= 0.15:
        return 3
    return 4


@router.get("/locus/{locus_tag}/research", response_model=ResearchStatus)
def get_research_status(locus_tag: str, db: Session = Depends(get_db)):
    """Full research status for a gene by locus_tag."""
    from openlab.db.models.evidence import Evidence

    gene = gene_service.get_gene_by_locus(db, locus_tag)
    evidence_rows = (
        db.query(Evidence)
        .filter(Evidence.gene_id == gene.gene_id)
        .order_by(Evidence.evidence_id)
        .all()
    )
    hyp = hypothesis_service.get_hypothesis_for_gene(db, gene.gene_id)
    convergence = gene_service.compute_convergence_score(db, gene.gene_id)
    report = gene_service.detect_disagreements(db, gene.gene_id)

    return ResearchStatus(
        gene_id=gene.gene_id,
        locus_tag=gene.locus_tag,
        stored=True,
        evidence=[EvidenceOut.model_validate(ev) for ev in evidence_rows],
        hypothesis=HypothesisDetail.model_validate(hyp) if hyp else None,
        convergence_score=convergence,
        tier=_convergence_tier(convergence),
        graduated=gene.graduated_at is not None,
        proposed_function=gene.proposed_function,
        disagreement_count=len(report.disagreeing_pairs),
    )


@router.patch("/locus/{locus_tag}/approve", response_model=GeneDetail)
def approve_gene(locus_tag: str, body: ApproveRequest, db: Session = Depends(get_db)):
    """Graduate a gene — approve its hypothesis."""
    gene = gene_service.get_gene_by_locus(db, locus_tag)
    hyp = hypothesis_service.get_hypothesis_for_gene(db, gene.gene_id)

    proposed_fn = body.proposed_function
    hypothesis_id = None
    if hyp:
        hypothesis_id = hyp.hypothesis_id
        if not proposed_fn:
            proposed_fn = gene_service.extract_proposed_function(hyp)

    if not proposed_fn:
        raise HTTPException(status_code=400, detail="No proposed_function provided and no hypothesis to extract from")

    try:
        gene = gene_service.graduate_gene(db, gene.gene_id, proposed_fn, hypothesis_id=hypothesis_id)
    except HypothesisNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if hyp:
        from openlab.db.models.hypothesis import HypothesisStatus
        hypothesis_service.update_hypothesis(db, hyp.hypothesis_id, status=HypothesisStatus.SUPPORTED)

    return gene


@router.patch("/locus/{locus_tag}/reject")
def reject_gene(locus_tag: str, db: Session = Depends(get_db)):
    """Reject the hypothesis for a gene."""
    gene = gene_service.get_gene_by_locus(db, locus_tag)
    hyp = hypothesis_service.get_hypothesis_for_gene(db, gene.gene_id)
    if not hyp:
        raise HTTPException(status_code=404, detail="No hypothesis to reject")

    from openlab.db.models.hypothesis import HypothesisStatus
    hypothesis_service.update_hypothesis(db, hyp.hypothesis_id, status=HypothesisStatus.REJECTED)
    return {"status": "rejected", "hypothesis_id": hyp.hypothesis_id}


@router.patch("/locus/{locus_tag}/correct", response_model=GeneDetail)
def correct_gene(locus_tag: str, body: CorrectRequest, db: Session = Depends(get_db)):
    """Correct a gene's function — ungraduate if needed, then re-graduate."""
    gene = gene_service.get_gene_by_locus(db, locus_tag)

    if gene.graduated_at is not None:
        gene_service.ungraduate_gene(db, gene.gene_id)

    hyp = hypothesis_service.get_hypothesis_for_gene(db, gene.gene_id)
    hypothesis_id = hyp.hypothesis_id if hyp else None

    gene = gene_service.graduate_gene(
        db, gene.gene_id, body.corrected_function, hypothesis_id=hypothesis_id
    )
    return gene


@router.get("/research/summary", response_model=ResearchSummary)
def get_research_summary(db: Session = Depends(get_db)):
    """Research progress summary across all genes."""
    from openlab.db.models.evidence import Evidence
    from openlab.db.models.hypothesis import Hypothesis, HypothesisStatus
    from sqlalchemy import func

    total_stored = db.query(Gene).count()
    total_with_evidence = (
        db.query(Gene.gene_id)
        .join(Evidence)
        .distinct()
        .count()
    )
    total_with_hypothesis = (
        db.query(Gene.gene_id)
        .join(Hypothesis, Hypothesis.gene_id == Gene.gene_id)
        .distinct()
        .count()
    )
    total_graduated = db.query(Gene).filter(Gene.graduated_at.isnot(None)).count()
    total_unknown = db.query(Gene).filter(
        Gene.graduated_at.is_(None),
        Gene.product.ilike("%hypothetical%"),
    ).count()

    # Needs review: genes with DRAFT hypotheses
    needs_review_rows = (
        db.query(Gene, Hypothesis)
        .join(Hypothesis, Hypothesis.gene_id == Gene.gene_id)
        .filter(Hypothesis.status == HypothesisStatus.DRAFT)
        .order_by(Hypothesis.confidence_score.desc())
        .limit(50)
        .all()
    )
    needs_review = [
        {
            "locus_tag": g.locus_tag,
            "product": g.product,
            "hypothesis_title": h.title,
            "confidence": h.confidence_score,
        }
        for g, h in needs_review_rows
    ]

    graduation_candidates = gene_service.list_graduation_candidates(db)

    disagreements = gene_service.detect_all_disagreements(db)

    return ResearchSummary(
        total_stored=total_stored,
        total_with_evidence=total_with_evidence,
        total_with_hypothesis=total_with_hypothesis,
        total_graduated=total_graduated,
        total_unknown=total_unknown,
        needs_review=needs_review,
        graduation_candidates=graduation_candidates[:20],
        disagreements=disagreements[:20],
    )
