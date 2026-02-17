"""Tests for VCF parser."""

from pathlib import Path

import pytest

from openlab.cancer.models.variant import GenomeBuild
from openlab.cancer.vcf.parser import VCFParseError, parse_vcf

VCF_FIXTURE = Path(__file__).parent.parent / "fixtures" / "vcf_files" / "sample.vcf"


def test_parse_vcf_basic():
    """Parse sample VCF and get expected variant count."""
    variants, metadata = parse_vcf(VCF_FIXTURE)
    assert len(variants) == 5
    assert metadata["total_variants"] == 5
    assert metadata["genome_build"] == "hg38"


def test_parse_vcf_variant_fields():
    """Parsed variants have correct fields."""
    variants, _ = parse_vcf(VCF_FIXTURE)

    # BRAF V600E
    braf = variants[0]
    assert braf.chrom == "chr7"
    assert braf.pos == 140753336
    assert braf.ref == "A"
    assert braf.alt == "T"
    assert braf.quality == 100.0
    assert braf.gene_symbol == "BRAF"
    assert braf.filter_status == "PASS"


def test_parse_vcf_gene_extraction():
    """Gene symbols are extracted from INFO field."""
    variants, _ = parse_vcf(VCF_FIXTURE)
    genes = [v.gene_symbol for v in variants]
    assert "BRAF" in genes
    assert "TP53" in genes
    assert "EGFR" in genes


def test_parse_vcf_metadata():
    """Metadata includes file hash and header info."""
    _, metadata = parse_vcf(VCF_FIXTURE)
    assert "file_hash" in metadata
    assert len(metadata["file_hash"]) == 64  # SHA-256 hex
    assert metadata["header_lines"] > 0


def test_parse_nonexistent_file():
    """Parsing a nonexistent file raises VCFParseError."""
    with pytest.raises(VCFParseError, match="not found"):
        parse_vcf("/tmp/nonexistent.vcf")


def test_parse_vcf_multiallelic():
    """Multi-allelic variants are decomposed."""
    import tempfile
    vcf_content = """##fileformat=VCFv4.2
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO
chr1\t100\t.\tA\tT,C\t50\tPASS\tGENE=TEST
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".vcf", delete=False) as f:
        f.write(vcf_content)
        f.flush()
        variants, _ = parse_vcf(f.name)

    assert len(variants) == 2
    assert variants[0].alt == "T"
    assert variants[1].alt == "C"


def test_parse_vcf_with_genome_build():
    """Genome build is stored in metadata."""
    _, metadata = parse_vcf(VCF_FIXTURE, GenomeBuild.HG19)
    assert metadata["genome_build"] == "hg19"
