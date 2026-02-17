"""Import service -- bridges parsers to DB."""

import tempfile
from pathlib import Path

from sqlalchemy.orm import Session

from openlab.exceptions import ImportError_, ParseError
from openlab.ingestion.genbank import ParsedGene, parse_genbank
from openlab.ingestion.fasta import parse_fasta
from openlab.db.models.gene import Gene
from openlab.db.models.genome import Genome


def _is_unknown_function(product: str | None) -> bool:
    """Check if a gene product indicates unknown function."""
    if not product:
        return True
    product_lower = product.lower()
    return any(
        term in product_lower
        for term in ["hypothetical", "uncharacterized", "unknown function", "putative"]
    )


def _parsed_gene_to_model(pg: ParsedGene) -> Gene:
    """Convert a parsed gene dataclass to a Gene ORM model."""
    essentiality = "unknown"

    return Gene(
        locus_tag=pg.locus_tag,
        name=pg.name,
        sequence=pg.sequence,
        protein_sequence=pg.protein_sequence,
        length=pg.length,
        strand=pg.strand,
        start=pg.start,
        end=pg.end,
        product=pg.product,
        essentiality=essentiality,
    )


def import_genbank(db: Session, path: Path | str) -> dict:
    """Import genes from a GenBank file into the database."""
    path = Path(path)
    if not path.exists():
        raise ImportError_(f"File not found: {path}")

    try:
        result = parse_genbank(path)
    except Exception as exc:
        raise ParseError(f"Failed to parse GenBank file: {exc}") from exc

    imported = 0
    skipped = 0
    for pg in result.genes:
        existing = db.query(Gene).filter(Gene.locus_tag == pg.locus_tag).first()
        if existing:
            skipped += 1
            continue

        gene = _parsed_gene_to_model(pg)
        db.add(gene)
        imported += 1

    db.commit()

    unknown_count = sum(
        1 for pg in result.genes if _is_unknown_function(pg.product)
    )

    return {
        "file": str(path),
        "accession": result.accession,
        "organism": result.organism,
        "total_features": len(result.genes),
        "imported": imported,
        "skipped": skipped,
        "unknown_function": unknown_count,
    }


def import_fasta(db: Session, path: Path | str) -> dict:
    """Import sequences from a FASTA file as genes (minimal info)."""
    path = Path(path)
    if not path.exists():
        raise ImportError_(f"File not found: {path}")

    try:
        entries = parse_fasta(path)
    except Exception as exc:
        raise ParseError(f"Failed to parse FASTA file: {exc}") from exc

    imported = 0
    skipped = 0
    for entry in entries:
        existing = db.query(Gene).filter(Gene.locus_tag == entry.id).first()
        if existing:
            skipped += 1
            continue

        gene = Gene(
            locus_tag=entry.id,
            sequence=entry.sequence,
            length=entry.length,
            strand=0,
            start=0,
            end=entry.length,
            notes=entry.description,
        )
        db.add(gene)
        imported += 1

    db.commit()
    return {
        "file": str(path),
        "total_entries": len(entries),
        "imported": imported,
        "skipped": skipped,
    }


def compute_gc_content(sequence: str) -> float:
    """Compute GC content as a percentage (0-100)."""
    if not sequence:
        return 0.0
    seq_upper = sequence.upper()
    gc = seq_upper.count("G") + seq_upper.count("C")
    return (gc / len(seq_upper)) * 100


def import_genome_from_text(db: Session, genbank_text: str) -> dict:
    """Parse GenBank text and import as a Genome + Genes atomically."""
    with tempfile.NamedTemporaryFile(suffix=".gb", mode="w", delete=False) as tmp:
        tmp.write(genbank_text)
        tmp_path = Path(tmp.name)

    try:
        result = parse_genbank(tmp_path)
    except Exception as exc:
        raise ParseError(f"Failed to parse GenBank text: {exc}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    # Check for duplicate
    existing = db.query(Genome).filter(Genome.accession == result.accession).first()
    if existing:
        return {"status": "duplicate", "genome_id": existing.genome_id}

    gc = compute_gc_content(result.genome_sequence)

    genome = Genome(
        accession=result.accession,
        organism=result.organism,
        description=result.description,
        genome_length=result.genome_length,
        is_circular=result.is_circular,
        gc_content=gc,
    )
    db.add(genome)
    db.flush()

    for pg in result.genes:
        gene = _parsed_gene_to_model(pg)
        gene.genome_id = genome.genome_id
        db.add(gene)

    db.commit()

    unknown_count = sum(1 for pg in result.genes if _is_unknown_function(pg.product))

    return {
        "status": "imported",
        "genome_id": genome.genome_id,
        "accession": result.accession,
        "organism": result.organism,
        "genome_length": result.genome_length,
        "gc_content": round(gc, 2),
        "total_genes": len(result.genes),
        "unknown_function": unknown_count,
    }
