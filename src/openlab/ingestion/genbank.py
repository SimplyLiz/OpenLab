"""BioPython GenBank parser -- pure function, no DB access."""

from dataclasses import dataclass, field
from pathlib import Path

from Bio import SeqIO


@dataclass
class ParsedGene:
    locus_tag: str
    sequence: str
    length: int
    strand: int
    start: int
    end: int
    name: str | None = None
    protein_sequence: str | None = None
    product: str | None = None
    gene_type: str = "CDS"  # CDS, rRNA, tRNA, etc.


@dataclass
class GenBankResult:
    accession: str
    organism: str
    description: str
    genes: list[ParsedGene] = field(default_factory=list)
    genome_sequence: str = ""
    genome_length: int = 0
    is_circular: bool = False


def parse_genbank(path: Path | str) -> GenBankResult:
    """Parse a GenBank file and extract all CDS and RNA features."""
    path = Path(path)
    record = SeqIO.read(path, "genbank")

    result = GenBankResult(
        accession=record.id,
        organism=record.annotations.get("organism", ""),
        description=record.description,
        genome_sequence=str(record.seq),
        genome_length=len(record.seq),
        is_circular="circular" in record.annotations.get("topology", ""),
    )

    for feature in record.features:
        if feature.type not in ("CDS", "rRNA", "tRNA", "ncRNA"):
            continue

        locus_tag = feature.qualifiers.get("locus_tag", [None])[0]
        if not locus_tag:
            continue

        location = feature.location
        strand = 1 if location.strand == 1 else -1
        start = int(location.start)
        end = int(location.end)

        nuc_seq = str(feature.extract(record.seq))

        protein_seq = None
        if feature.type == "CDS":
            translations = feature.qualifiers.get("translation", [])
            if translations:
                protein_seq = translations[0]

        gene_name = feature.qualifiers.get("gene", [None])[0]
        product = feature.qualifiers.get("product", [None])[0]

        result.genes.append(
            ParsedGene(
                locus_tag=locus_tag,
                name=gene_name,
                sequence=nuc_seq,
                protein_sequence=protein_seq,
                length=end - start,
                strand=strand,
                start=start,
                end=end,
                product=product,
                gene_type=feature.type,
            )
        )

    return result
