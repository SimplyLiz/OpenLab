"""Genome API endpoints — multi-genome support."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from openlab.api.deps import get_db
from openlab.db.models.gene import Gene
from openlab.db.models.genome import Genome

log = logging.getLogger(__name__)

router = APIRouter(prefix="/genomes", tags=["genomes"])


# ── Schemas ────────────────────────────────────────────────────────────


class GenomeSummary(BaseModel):
    genome_id: int
    accession: str
    organism: str
    genome_length: int
    gc_content: float | None = None
    is_circular: bool = False
    total_genes: int = 0
    genes_known: int = 0
    genes_unknown: int = 0
    description: str | None = None

    model_config = {"from_attributes": True}


class GenomeDetail(GenomeSummary):
    pass


class NCBISearchResult(BaseModel):
    accession: str
    organism: str
    title: str
    length: int


class GenomeFetchRequest(BaseModel):
    accession: str


class GenomeFetchResponse(BaseModel):
    status: str
    genome_id: int | None = None
    accession: str | None = None
    organism: str | None = None
    genome_length: int | None = None
    gc_content: float | None = None
    total_genes: int | None = None
    message: str | None = None


# ── Endpoints ──────────────────────────────────────────────────────────


@router.get("", response_model=list[GenomeSummary])
def list_genomes(db: Session = Depends(get_db)):
    """List all genomes with summary stats."""
    genomes = db.query(Genome).order_by(Genome.genome_id).all()
    results = []
    for g in genomes:
        total = db.query(func.count(Gene.gene_id)).filter(Gene.genome_id == g.genome_id).scalar() or 0
        unknown = (
            db.query(func.count(Gene.gene_id))
            .filter(
                Gene.genome_id == g.genome_id,
                Gene.graduated_at.is_(None),
                Gene.product.ilike("%hypothetical%"),
            )
            .scalar() or 0
        )
        results.append(GenomeSummary(
            genome_id=g.genome_id,
            accession=g.accession,
            organism=g.organism,
            genome_length=g.genome_length,
            gc_content=g.gc_content,
            is_circular=g.is_circular,
            total_genes=total,
            genes_known=total - unknown,
            genes_unknown=unknown,
            description=g.description,
        ))
    return results


@router.get("/search", response_model=list[NCBISearchResult])
def search_ncbi_genomes(
    q: str = Query(..., min_length=2),
    max_results: int = Query(20, le=50),
):
    """Search NCBI for bacterial genomes."""
    from openlab.services.ncbi_genomes import search_genomes

    try:
        results = search_genomes(q, max_results)
    except Exception as exc:
        log.error("NCBI search failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"NCBI search failed: {exc}")
    return results


@router.post("/fetch", response_model=GenomeFetchResponse)
def fetch_ncbi_genome(
    body: GenomeFetchRequest,
    db: Session = Depends(get_db),
):
    """Fetch a genome from NCBI by accession and import it."""
    from openlab.services.ncbi_genomes import fetch_genbank
    from openlab.services.import_service import import_genome_from_text
    from openlab.exceptions import ParseError

    try:
        genbank_text = fetch_genbank(body.accession)
    except Exception as exc:
        log.error("NCBI fetch failed for %s: %s", body.accession, exc)
        raise HTTPException(status_code=502, detail=f"NCBI fetch failed: {exc}")

    try:
        result = import_genome_from_text(db, genbank_text)
    except ParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return GenomeFetchResponse(**result)


@router.get("/{genome_id}", response_model=GenomeDetail)
def get_genome(genome_id: int, db: Session = Depends(get_db)):
    """Get genome detail by ID."""
    g = db.query(Genome).filter(Genome.genome_id == genome_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Genome not found")

    total = db.query(func.count(Gene.gene_id)).filter(Gene.genome_id == g.genome_id).scalar() or 0
    unknown = (
        db.query(func.count(Gene.gene_id))
        .filter(
            Gene.genome_id == g.genome_id,
            Gene.graduated_at.is_(None),
            Gene.product.ilike("%hypothetical%"),
        )
        .scalar() or 0
    )
    return GenomeDetail(
        genome_id=g.genome_id,
        accession=g.accession,
        organism=g.organism,
        genome_length=g.genome_length,
        gc_content=g.gc_content,
        is_circular=g.is_circular,
        total_genes=total,
        genes_known=total - unknown,
        genes_unknown=unknown,
        description=g.description,
    )


@router.get("/{genome_id}/hydrate")
def genome_hydrate(genome_id: int, db: Session = Depends(get_db)):
    """Full GenomeRecord with genes for a specific genome.

    Replaces the old hardcoded /genes/genome/hydrate endpoint.
    """
    from openlab.models import FunctionalCategory, GenomeGene, GenomeRecord
    from openlab.services.genbank import _classify_gene, CATEGORY_COLORS
    from openlab.services.prior_knowledge import lookup
    from openlab.db.models.hypothesis import Hypothesis

    genome = db.query(Genome).filter(Genome.genome_id == genome_id).first()
    if not genome:
        raise HTTPException(status_code=404, detail="Genome not found")

    genes = (
        db.query(Gene)
        .filter(Gene.genome_id == genome_id)
        .order_by(Gene.start)
        .all()
    )
    if not genes:
        raise HTTPException(status_code=404, detail="No genes for this genome")

    # Pre-load best hypothesis per gene (single query)
    gene_ids = [g.gene_id for g in genes]
    hyp_rows = (
        db.query(Hypothesis)
        .filter(Hypothesis.gene_id.in_(gene_ids))
        .order_by(Hypothesis.confidence_score.desc())
        .all()
    )
    best_hyp: dict[int, Hypothesis] = {}
    for h in hyp_rows:
        if h.gene_id not in best_hyp:
            best_hyp[h.gene_id] = h

    from openlab.services import gene_service

    genome_genes: list[GenomeGene] = []
    for g in genes:
        if g.graduated_at is not None:
            category = FunctionalCategory.PREDICTED
            color = "#34d399"
            source = "genelife"
        elif g.gene_id in best_hyp:
            hyp = best_hyp[g.gene_id]
            proposed_fn = gene_service.extract_proposed_function(hyp)
            category, _ = _classify_gene(proposed_fn, g.name or "")
            if category == FunctionalCategory.UNKNOWN:
                category = FunctionalCategory.PREDICTED
            color = CATEGORY_COLORS.get(category, "#fb923c")
            source = "genelife"
        else:
            prior = lookup(g.locus_tag)
            if prior:
                category = FunctionalCategory.PREDICTED
                color = "#fb923c"
                source = "dnasyn" if "dnasyn" in prior.source else "curated"
            else:
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

    record = GenomeRecord(
        accession=genome.accession,
        organism=genome.organism,
        description=genome.description or "",
        genome_length=genome.genome_length,
        is_circular=genome.is_circular,
        gc_content=genome.gc_content or 0.0,
        genes=genome_genes,
        total_genes=total,
        genes_known=known,
        genes_predicted=predicted,
        genes_unknown=unknown,
    )

    return record.model_dump()
