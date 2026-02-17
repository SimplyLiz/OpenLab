"""Transposon mutagenesis data parser (Hutchison et al. 2016)."""

import csv
from dataclasses import dataclass
from pathlib import Path

from openlab.exceptions import ParseError


@dataclass
class TransposonEntry:
    locus_tag: str
    essentiality: str  # essential | quasi-essential | non-essential | disrupted
    tn5_class: str     # e | i | n | d
    n_insertions: int
    notes: str | None = None


VALID_CLASSES = {"e", "i", "n", "d"}
VALID_ESSENTIALITIES = {"essential", "quasi-essential", "non-essential", "disrupted"}


def parse_transposon_tsv(path: Path | str) -> list[TransposonEntry]:
    """Parse a TSV file of transposon essentiality data.

    Expected columns: locus_tag, essentiality, tn5_class, n_insertions, notes
    """
    path = Path(path)
    if not path.exists():
        raise ParseError(f"File not found: {path}")

    entries: list[TransposonEntry] = []

    with open(path, newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")

        required = {"locus_tag", "essentiality", "tn5_class", "n_insertions"}
        if reader.fieldnames is None:
            raise ParseError("Empty TSV file")
        missing = required - set(reader.fieldnames)
        if missing:
            raise ParseError(f"Missing required columns: {missing}")

        for lineno, row in enumerate(reader, start=2):
            locus = row["locus_tag"].strip()
            if not locus:
                raise ParseError(f"Line {lineno}: empty locus_tag")

            tn5_class = row["tn5_class"].strip().lower()
            if tn5_class not in VALID_CLASSES:
                raise ParseError(
                    f"Line {lineno}: invalid tn5_class '{tn5_class}', "
                    f"expected one of {VALID_CLASSES}"
                )

            essentiality = row["essentiality"].strip().lower()
            if essentiality not in VALID_ESSENTIALITIES:
                raise ParseError(
                    f"Line {lineno}: invalid essentiality '{essentiality}', "
                    f"expected one of {VALID_ESSENTIALITIES}"
                )

            try:
                n_ins = int(row["n_insertions"].strip())
            except ValueError:
                raise ParseError(
                    f"Line {lineno}: n_insertions must be an integer, "
                    f"got '{row['n_insertions']}'"
                )

            notes = row.get("notes", "").strip() or None

            entries.append(
                TransposonEntry(
                    locus_tag=locus,
                    essentiality=essentiality,
                    tn5_class=tn5_class,
                    n_insertions=n_ins,
                    notes=notes,
                )
            )

    if not entries:
        raise ParseError("No data rows in TSV file")

    return entries
