"""Tests for HGVS converter."""

from openlab.cancer.models.variant import GenomeBuild, VariantRecord
from openlab.cancer.vcf.hgvs_converter import add_hgvs_to_variants, vcf_to_hgvs_g


def test_snv_hgvs():
    """SNV converts to proper HGVS g. notation."""
    v = VariantRecord(chrom="chr17", pos=7674220, ref="C", alt="T")
    hgvs = vcf_to_hgvs_g(v, GenomeBuild.HG38)
    assert hgvs == "NC_000017.11:g.7674220C>T"


def test_snv_hgvs_hg19():
    """SNV with hg19 uses correct accession version."""
    v = VariantRecord(chrom="17", pos=7674220, ref="C", alt="T")
    hgvs = vcf_to_hgvs_g(v, GenomeBuild.HG19)
    assert hgvs == "NC_000017.10:g.7674220C>T"


def test_deletion_hgvs():
    """Deletion converts correctly."""
    v = VariantRecord(chrom="chr7", pos=100, ref="AT", alt="A")
    hgvs = vcf_to_hgvs_g(v, GenomeBuild.HG38)
    assert hgvs == "NC_000007.14:g.101del"


def test_multi_base_deletion_hgvs():
    """Multi-base deletion uses range notation."""
    v = VariantRecord(chrom="chr7", pos=100, ref="ATCG", alt="A")
    hgvs = vcf_to_hgvs_g(v, GenomeBuild.HG38)
    assert hgvs == "NC_000007.14:g.101_103del"


def test_insertion_hgvs():
    """Insertion converts correctly."""
    v = VariantRecord(chrom="chr7", pos=100, ref="A", alt="ATG")
    hgvs = vcf_to_hgvs_g(v, GenomeBuild.HG38)
    assert hgvs == "NC_000007.14:g.100_101insTG"


def test_chr_prefix_stripped():
    """Chromosome prefix 'chr' is handled."""
    v1 = VariantRecord(chrom="chr17", pos=100, ref="A", alt="T")
    v2 = VariantRecord(chrom="17", pos=100, ref="A", alt="T")
    assert vcf_to_hgvs_g(v1, GenomeBuild.HG38) == vcf_to_hgvs_g(v2, GenomeBuild.HG38)


def test_unknown_chrom():
    """Unknown chromosome returns empty string."""
    v = VariantRecord(chrom="chrUn_random", pos=100, ref="A", alt="T")
    assert vcf_to_hgvs_g(v, GenomeBuild.HG38) == ""


def test_add_hgvs_to_variants():
    """add_hgvs_to_variants populates hgvs_g field."""
    variants = [
        VariantRecord(chrom="chr17", pos=7674220, ref="C", alt="T"),
        VariantRecord(chrom="chr7", pos=140753336, ref="A", alt="T"),
    ]
    result = add_hgvs_to_variants(variants, GenomeBuild.HG38)
    assert all(v.hgvs_g for v in result)
    assert "NC_000017.11" in result[0].hgvs_g
    assert "NC_000007.14" in result[1].hgvs_g
