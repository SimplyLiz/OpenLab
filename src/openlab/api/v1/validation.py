"""Validation API endpoints — trigger and retrieve validation results."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from openlab.db.engine import get_db
from openlab.services import validation_service

router = APIRouter(prefix="/validation", tags=["validation"])


@router.post("/run")
def run_validation(
    bootstrap: bool = False,
    bootstrap_limit: int = 20,
    db: Session = Depends(get_db),
):
    """Trigger full validation suite (ortholog + consistency + optional bootstrap)."""
    report = validation_service.validate_all(
        db,
        run_bootstrap=bootstrap,
        bootstrap_limit=bootstrap_limit,
    )
    return report


@router.get("/results")
def get_results(db: Session = Depends(get_db)):
    """Get latest validation report (ortholog accuracy, consistency rate, FPR)."""
    report = validation_service.validate_all(db)
    return report["summary"]


@router.get("/tiers")
def get_tiers(db: Session = Depends(get_db)):
    """Get confidence tier breakdown for graduated genes."""
    return validation_service.build_confidence_tiers(db)


@router.get("/genes/{gene_id}")
def get_gene_validation(gene_id: int, db: Session = Depends(get_db)):
    """Per-gene validation status: convergence, ortholog, consistency checks."""
    from openlab.services.gene_service import get_gene, compute_convergence_score
    from openlab.db.models.evidence import Evidence

    gene = get_gene(db, gene_id)

    # Convergence
    conv_score = compute_convergence_score(db, gene_id)

    # Evidence count
    ev_count = db.query(Evidence).filter(Evidence.gene_id == gene_id).count()

    # Check if gene appears in ortholog/consistency results
    orth_results = validation_service.ortholog_validation(db)
    cons_results = validation_service.consistency_validation(db)

    orth_entry = next((r for r in orth_results if r["gene_id"] == gene_id), None)
    cons_entry = next((r for r in cons_results if r["gene_id"] == gene_id), None)

    return {
        "gene_id": gene_id,
        "locus_tag": gene.locus_tag,
        "proposed_function": gene.proposed_function,
        "graduated": gene.graduated_at is not None,
        "convergence_score": conv_score,
        "evidence_count": ev_count,
        "ortholog_validation": orth_entry,
        "consistency_validation": cons_entry,
    }
