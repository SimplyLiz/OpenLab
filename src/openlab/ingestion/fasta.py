"""FASTA parser -- pure function, no DB access."""

from dataclasses import dataclass
from pathlib import Path

from Bio import SeqIO


@dataclass
class FastaEntry:
    id: str
    description: str
    sequence: str
    length: int


def parse_fasta(path: Path | str) -> list[FastaEntry]:
    """Parse a FASTA file and return list of entries."""
    path = Path(path)
    entries = []
    for record in SeqIO.parse(path, "fasta"):
        entries.append(
            FastaEntry(
                id=record.id,
                description=record.description,
                sequence=str(record.seq),
                length=len(record.seq),
            )
        )
    return entries
