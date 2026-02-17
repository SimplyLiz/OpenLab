"""Tests for transposon import service."""

from pathlib import Path

from openlab.db.models import Evidence, EvidenceType, Gene
from openlab.services import transposon_service

FIXTURE = Path(__file__).parent.parent / "fixtures" / "mini_transposon.tsv"


def _seed_genes(db):
    """Create genes matching the mini fixture locus tags."""
    tags = [
        "JCVISYN3A_0001",
        "JCVISYN3A_0002",
        "JCVISYN3A_0003",
        "JCVISYN3A_0004",
    ]
    genes = []
    for i, tag in enumerate(tags):
        g = Gene(
            locus_tag=tag,
            sequence="ATG",
            length=3,
            strand=1,
            start=i * 1000,
            end=i * 1000 + 3,
        )
        db.add(g)
        genes.append(g)
    db.flush()
    return genes


def test_import_transposon_data(db):
    genes = _seed_genes(db)
    result = transposon_service.import_transposon_data(db, FIXTURE)

    assert result["total_entries"] == 4
    assert result["imported"] == 4
    assert result["skipped"] == 0
    assert result["genes_updated"] == 4


def test_evidence_created(db):
    _seed_genes(db)
    transposon_service.import_transposon_data(db, FIXTURE)

    ev_list = (
        db.query(Evidence)
        .filter(Evidence.evidence_type == EvidenceType.TRANSPOSON)
        .all()
    )
    assert len(ev_list) == 4

    # Check first evidence
    ev = (
        db.query(Evidence)
        .join(Gene)
        .filter(
            Gene.locus_tag == "JCVISYN3A_0001",
            Evidence.evidence_type == EvidenceType.TRANSPOSON,
        )
        .first()
    )
    assert ev is not None
    assert ev.payload["tn5_class"] == "e"
    assert ev.payload["source"] == "Hutchison2016"
    assert ev.confidence == 0.95


def test_gene_essentiality_updated(db):
    _seed_genes(db)
    transposon_service.import_transposon_data(db, FIXTURE)

    gene = db.query(Gene).filter(Gene.locus_tag == "JCVISYN3A_0001").first()
    assert gene.essentiality == "essential"

    gene3 = db.query(Gene).filter(Gene.locus_tag == "JCVISYN3A_0003").first()
    assert gene3.essentiality == "non-essential"


def test_no_duplicates(db):
    _seed_genes(db)
    transposon_service.import_transposon_data(db, FIXTURE)
    result2 = transposon_service.import_transposon_data(db, FIXTURE)

    # Second import should skip all (duplicates)
    assert result2["imported"] == 0
    assert result2["skipped"] == 4


def test_missing_genes_skipped(db):
    # Only create one gene
    g = Gene(
        locus_tag="JCVISYN3A_0001",
        sequence="ATG",
        length=3,
        strand=1,
        start=0,
        end=3,
    )
    db.add(g)
    db.flush()

    result = transposon_service.import_transposon_data(db, FIXTURE)
    assert result["imported"] == 1
    assert result["skipped"] == 3
