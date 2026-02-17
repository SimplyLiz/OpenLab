"""VCF file parser.

Provides a pure-Python VCF parser that handles standard VCF 4.x format.
For production use, cyvcf2 is preferred but optional. This parser covers
the common case without requiring the C library dependency.
"""

from __future__ import annotations

import contextlib
import hashlib
import logging
from pathlib import Path
from typing import Any

from openlab.cancer.models.variant import GenomeBuild, VariantRecord

logger = logging.getLogger(__name__)


class VCFParseError(Exception):
    """Raised when VCF parsing fails."""


def parse_vcf(
    vcf_path: str | Path,
    genome_build: GenomeBuild = GenomeBuild.HG38,
) -> tuple[list[VariantRecord], dict[str, Any]]:
    """Parse a VCF file and return variant records + metadata.

    Returns:
        (variants, metadata) where metadata includes sample info, contig lines, etc.
    """
    path = Path(vcf_path)
    if not path.exists():
        raise VCFParseError(f"VCF file not found: {path}")

    variants: list[VariantRecord] = []
    metadata: dict[str, Any] = {
        "file_path": str(path),
        "file_hash": _sha256(path),
        "genome_build": genome_build.value,
        "header_lines": 0,
        "samples": [],
    }

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if line.startswith("##"):
                metadata["header_lines"] += 1
                _parse_meta_line(line, metadata)
                continue

            if line.startswith("#CHROM"):
                metadata["header_lines"] += 1
                parts = line.split("\t")
                if len(parts) > 9:
                    metadata["samples"] = parts[9:]
                continue

            # Data line
            try:
                variant = _parse_data_line(line)
                if variant:
                    # Handle multi-allelic: split into separate records
                    for v in _decompose_multiallelic(variant):
                        variants.append(v)
            except Exception as e:
                logger.warning("Skipping malformed VCF line: %s", e)

    metadata["total_variants"] = len(variants)
    return variants, metadata


def _parse_data_line(line: str) -> VariantRecord | None:
    """Parse a single VCF data line."""
    parts = line.split("\t")
    if len(parts) < 8:
        return None

    chrom = parts[0]
    try:
        pos = int(parts[1])
    except ValueError:
        return None

    ref = parts[3].upper()
    alt = parts[4].upper()

    quality = None
    if parts[5] != ".":
        with contextlib.suppress(ValueError):
            quality = float(parts[5])

    filter_status = parts[6]

    info = _parse_info(parts[7]) if len(parts) > 7 else {}

    gene_symbol = info.get("GENE", "") or info.get("Gene", "") or info.get("ANN_Gene", "")

    return VariantRecord(
        chrom=chrom,
        pos=pos,
        ref=ref,
        alt=alt,
        quality=quality,
        filter_status=filter_status,
        gene_symbol=gene_symbol,
        info=info,
    )


def _decompose_multiallelic(variant: VariantRecord) -> list[VariantRecord]:
    """Split multi-allelic variants (ALT with commas) into separate records."""
    alts = variant.alt.split(",")
    if len(alts) == 1:
        return [variant]

    result = []
    for alt in alts:
        v = variant.model_copy(update={"alt": alt.strip()})
        result.append(v)
    return result


def _parse_info(info_str: str) -> dict[str, str]:
    """Parse VCF INFO field into a dict."""
    if info_str == ".":
        return {}

    result = {}
    for field in info_str.split(";"):
        if "=" in field:
            key, value = field.split("=", 1)
            result[key] = value
        else:
            result[field] = "true"
    return result


def _parse_meta_line(line: str, metadata: dict) -> None:
    """Extract useful metadata from ## lines."""
    if line.startswith("##reference="):
        metadata["reference"] = line.split("=", 1)[1]
    elif line.startswith("##source="):
        metadata["vcf_source"] = line.split("=", 1)[1]


def _sha256(path: Path) -> str:
    """Compute SHA-256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
