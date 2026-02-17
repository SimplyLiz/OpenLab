from pathlib import Path

from openlab.db.models.gene import Gene
from openlab.services.import_service import import_genbank

FIXTURE = Path(__file__).parent.parent / "fixtures" / "mini_syn3a.gb"


def test_import_genbank(db):
    result = import_genbank(db, FIXTURE)
    assert result["imported"] == 4
    assert result["skipped"] == 0

    genes = db.query(Gene).all()
    assert len(genes) == 4


def test_import_genbank_idempotent(db):
    import_genbank(db, FIXTURE)
    result = import_genbank(db, FIXTURE)
    assert result["imported"] == 0
    assert result["skipped"] == 4

    genes = db.query(Gene).all()
    assert len(genes) == 4
