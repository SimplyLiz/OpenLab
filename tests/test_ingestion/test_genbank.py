from pathlib import Path

from openlab.ingestion.genbank import parse_genbank

FIXTURE = Path(__file__).parent.parent / "fixtures" / "mini_syn3a.gb"


def test_parse_genbank_counts():
    result = parse_genbank(FIXTURE)
    # 3 CDS + 1 tRNA = 4 genes
    assert len(result.genes) == 4
    assert result.accession == "CP016816.2"


def test_parse_genbank_cds():
    result = parse_genbank(FIXTURE)
    dnaA = next(g for g in result.genes if g.locus_tag == "JCVISYN3A_0001")
    assert dnaA.name == "dnaA"
    assert dnaA.product == "chromosomal replication initiator protein DnaA"
    assert dnaA.strand == 1
    assert dnaA.protein_sequence is not None
    assert dnaA.gene_type == "CDS"


def test_parse_genbank_hypothetical():
    result = parse_genbank(FIXTURE)
    hyp = next(g for g in result.genes if g.locus_tag == "JCVISYN3A_0002")
    assert hyp.name is None
    assert "hypothetical" in hyp.product.lower()


def test_parse_genbank_trna():
    result = parse_genbank(FIXTURE)
    trna = next(g for g in result.genes if g.locus_tag == "JCVISYN3A_0003")
    assert trna.gene_type == "tRNA"
    assert trna.protein_sequence is None
