from openlab.db.models import Gene, ProteinFeature


def test_create_gene(db):
    gene = Gene(
        locus_tag="JCVISYN3A_0001",
        name="dnaA",
        sequence="ATGCGATCG",
        protein_sequence="MRI",
        length=9,
        strand=1,
        start=1,
        end=9,
        product="chromosomal replication initiator protein DnaA",
        essentiality="essential",
    )
    db.add(gene)
    db.flush()

    assert gene.gene_id is not None
    assert gene.locus_tag == "JCVISYN3A_0001"
    assert repr(gene) == "<Gene JCVISYN3A_0001 (dnaA)>"


def test_gene_unknown_name(db):
    gene = Gene(
        locus_tag="JCVISYN3A_0999",
        sequence="ATG",
        length=3,
        strand=-1,
        start=100,
        end=103,
    )
    db.add(gene)
    db.flush()

    assert gene.name is None
    assert repr(gene) == "<Gene JCVISYN3A_0999 (unknown)>"


def test_protein_feature_relationship(db):
    gene = Gene(
        locus_tag="JCVISYN3A_0002",
        sequence="ATGCCC",
        length=6,
        strand=1,
        start=10,
        end=16,
    )
    db.add(gene)
    db.flush()

    feat = ProteinFeature(
        gene_id=gene.gene_id,
        feature_type="domain",
        start=1,
        end=50,
        score=0.99,
        source="Pfam",
        source_version="36.0",
    )
    db.add(feat)
    db.flush()

    assert len(gene.features) == 1
    assert gene.features[0].feature_type == "domain"
    assert feat.gene.locus_tag == "JCVISYN3A_0002"
