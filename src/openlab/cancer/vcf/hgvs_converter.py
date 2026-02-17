"""VCF coordinates to HGVS notation converter.

Provides a lightweight converter for generating HGVS genomic notation (g.)
from VCF records. For full c. and p. notation, the biocommons.hgvs library
is used when available.
"""

from __future__ import annotations

import logging

from openlab.cancer.models.variant import GenomeBuild, VariantRecord

logger = logging.getLogger(__name__)

# Chromosome to RefSeq accession mapping (GRCh38)
_CHROM_TO_REFSEQ_38: dict[str, str] = {
    "1": "NC_000001.11", "2": "NC_000002.12", "3": "NC_000003.12",
    "4": "NC_000004.12", "5": "NC_000005.10", "6": "NC_000006.12",
    "7": "NC_000007.14", "8": "NC_000008.11", "9": "NC_000009.12",
    "10": "NC_000010.11", "11": "NC_000011.10", "12": "NC_000012.12",
    "13": "NC_000013.11", "14": "NC_000014.9", "15": "NC_000015.10",
    "16": "NC_000016.10", "17": "NC_000017.11", "18": "NC_000018.10",
    "19": "NC_000019.10", "20": "NC_000020.11", "21": "NC_000021.9",
    "22": "NC_000022.11", "X": "NC_000023.11", "Y": "NC_000024.10",
}

_CHROM_TO_REFSEQ_37: dict[str, str] = {
    "1": "NC_000001.10", "2": "NC_000002.11", "3": "NC_000003.11",
    "4": "NC_000004.11", "5": "NC_000005.9", "6": "NC_000006.11",
    "7": "NC_000007.13", "8": "NC_000008.10", "9": "NC_000009.11",
    "10": "NC_000010.10", "11": "NC_000011.9", "12": "NC_000012.11",
    "13": "NC_000013.10", "14": "NC_000014.8", "15": "NC_000015.9",
    "16": "NC_000016.9", "17": "NC_000017.10", "18": "NC_000018.9",
    "19": "NC_000019.9", "20": "NC_000020.10", "21": "NC_000021.8",
    "22": "NC_000022.10", "X": "NC_000023.10", "Y": "NC_000024.9",
}


def vcf_to_hgvs_g(variant: VariantRecord, genome_build: GenomeBuild) -> str:
    """Convert VCF record to HGVS genomic (g.) notation.

    Examples:
        SNV: NC_000017.11:g.7674220C>T
        Deletion: NC_000017.11:g.7674220_7674221del
        Insertion: NC_000017.11:g.7674220_7674221insATG
    """
    chrom = _normalize_chrom(variant.chrom)
    refseq_map = _CHROM_TO_REFSEQ_38 if genome_build.is_hg38() else _CHROM_TO_REFSEQ_37
    accession = refseq_map.get(chrom, "")

    if not accession:
        return ""

    ref = variant.ref
    alt = variant.alt

    if len(ref) == 1 and len(alt) == 1:
        # SNV
        return f"{accession}:g.{variant.pos}{ref}>{alt}"
    elif len(ref) > len(alt):
        # Deletion
        if alt == ref[0]:
            # Simple deletion
            del_start = variant.pos + 1
            del_end = variant.pos + len(ref) - 1
            if del_start == del_end:
                return f"{accession}:g.{del_start}del"
            return f"{accession}:g.{del_start}_{del_end}del"
        else:
            # Complex indel — delins
            return f"{accession}:g.{variant.pos}_{variant.pos + len(ref) - 1}delins{alt}"
    elif len(alt) > len(ref):
        # Insertion
        if ref == alt[0]:
            ins_seq = alt[1:]
            return f"{accession}:g.{variant.pos}_{variant.pos + 1}ins{ins_seq}"
        else:
            return f"{accession}:g.{variant.pos}_{variant.pos + len(ref) - 1}delins{alt}"
    else:
        # MNV — multi-nucleotide variant
        return f"{accession}:g.{variant.pos}_{variant.pos + len(ref) - 1}delins{alt}"


def add_hgvs_to_variants(
    variants: list[VariantRecord],
    genome_build: GenomeBuild,
) -> list[VariantRecord]:
    """Add HGVS genomic notation to a list of variants."""
    for v in variants:
        if not v.hgvs_g:
            v.hgvs_g = vcf_to_hgvs_g(v, genome_build)
    return variants


def _normalize_chrom(chrom: str) -> str:
    """Normalize chromosome name: strip 'chr' prefix."""
    chrom = chrom.strip()
    if chrom.lower().startswith("chr"):
        chrom = chrom[3:]
    return chrom
