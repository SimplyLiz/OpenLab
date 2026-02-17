"""Dashboard data layer — cached DB queries for Streamlit pages."""

from __future__ import annotations

import os
import sys

# Ensure biolab package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import streamlit as st
from sqlalchemy import func
from sqlalchemy.orm import Session

from biolab.db.engine import get_session_factory
from biolab.db.models.evidence import Evidence, EvidenceType
from biolab.db.models.gene import Gene, ProteinFeature
from biolab.db.models.hypothesis import Hypothesis


def get_db() -> Session:
    factory = get_session_factory()
    return factory()


@st.cache_data(ttl=300)
def get_gene_count() -> int:
    db = get_db()
    try:
        return db.query(Gene).count()
    finally:
        db.close()


@st.cache_data(ttl=300)
def get_evidence_count() -> int:
    db = get_db()
    try:
        return db.query(Evidence).count()
    finally:
        db.close()


@st.cache_data(ttl=300)
def get_hypothesis_count() -> int:
    db = get_db()
    try:
        return db.query(Hypothesis).count()
    finally:
        db.close()


@st.cache_data(ttl=300)
def get_graduated_count() -> int:
    db = get_db()
    try:
        return db.query(Gene).filter(Gene.graduated_at.isnot(None)).count()
    finally:
        db.close()


@st.cache_data(ttl=300)
def get_genes_df() -> list[dict]:
    """Get all genes as list of dicts for dataframe display."""
    db = get_db()
    try:
        genes = db.query(Gene).order_by(Gene.start).all()
        return [
            {
                "gene_id": g.gene_id,
                "locus_tag": g.locus_tag,
                "name": g.name or "",
                "product": g.product or "hypothetical protein",
                "start": g.start,
                "end": g.end,
                "strand": "+" if g.strand == 1 else "-",
                "length": g.length,
                "essentiality": g.essentiality or "unknown",
                "proposed_function": g.proposed_function or "",
                "graduated": g.graduated_at is not None,
            }
            for g in genes
        ]
    finally:
        db.close()


@st.cache_data(ttl=300)
def get_evidence_by_type() -> dict[str, int]:
    """Count evidence records by type."""
    db = get_db()
    try:
        rows = (
            db.query(Evidence.evidence_type, func.count())
            .group_by(Evidence.evidence_type)
            .all()
        )
        return {et.value: cnt for et, cnt in rows}
    finally:
        db.close()


@st.cache_data(ttl=300)
def get_evidence_by_source() -> dict[str, int]:
    """Count evidence records by source_ref."""
    db = get_db()
    try:
        rows = (
            db.query(Evidence.source_ref, func.count())
            .group_by(Evidence.source_ref)
            .all()
        )
        return {(src or "unknown"): cnt for src, cnt in rows}
    finally:
        db.close()


@st.cache_data(ttl=300)
def get_gene_evidence_counts() -> dict[int, int]:
    """Evidence count per gene."""
    db = get_db()
    try:
        rows = (
            db.query(Evidence.gene_id, func.count())
            .group_by(Evidence.gene_id)
            .all()
        )
        return dict(rows)
    finally:
        db.close()


@st.cache_data(ttl=60)
def get_gene_detail(gene_id: int) -> dict | None:
    """Full gene detail with evidence and features."""
    db = get_db()
    try:
        from biolab.services.gene_service import get_dossier
        return get_dossier(db, gene_id)
    except Exception:
        return None
    finally:
        db.close()


@st.cache_data(ttl=300)
def get_hypotheses_df() -> list[dict]:
    """Get all hypotheses as list of dicts."""
    db = get_db()
    try:
        hyps = db.query(Hypothesis).order_by(Hypothesis.hypothesis_id.desc()).all()
        return [
            {
                "hypothesis_id": h.hypothesis_id,
                "gene_id": h.gene_id,
                "title": h.title,
                "confidence_score": h.confidence_score or 0,
                "convergence_score": h.convergence_score or 0,
                "status": h.status.value if h.status else "pending",
            }
            for h in hyps
        ]
    finally:
        db.close()


@st.cache_data(ttl=300)
def get_validation_summary() -> dict:
    """Get latest validation summary."""
    db = get_db()
    try:
        from biolab.services import validation_service
        report = validation_service.validate_all(db)
        return report.get("summary", {})
    except Exception:
        return {}
    finally:
        db.close()


@st.cache_data(ttl=300)
def get_confidence_tiers() -> dict:
    """Get confidence tier breakdown."""
    db = get_db()
    try:
        from biolab.services import validation_service
        return validation_service.build_confidence_tiers(db)
    except Exception:
        return {"tiers": {}, "summary": {"total_graduated": 0, "tier_breakdown": {}}}
    finally:
        db.close()
