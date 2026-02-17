"""GenBank genome fetcher — parses whole genomes into gene lists.

Handles synthetic genomes like JCVI-syn1.0/2.0/3.0/3A.
"""

from __future__ import annotations

import io
from typing import Any

import httpx
from Bio import SeqIO

from openlab.config import config
from openlab.models import FunctionalCategory, GenomeGene, GenomeRecord

# Known synthetic organism accessions
SYNTHETIC_GENOMES: dict[str, dict[str, str]] = {
    "jcvi-syn1.0": {"accession": "CP002027.1", "name": "Mycoplasma mycoides JCVI-syn1.0"},
    "jcvi-syn1":   {"accession": "CP002027.1", "name": "Mycoplasma mycoides JCVI-syn1.0"},
    "syn1.0":      {"accession": "CP002027.1", "name": "Mycoplasma mycoides JCVI-syn1.0"},
    "jcvi-syn2.0": {"accession": "CP014992.1", "name": "Synthetic Mycoplasma mycoides JCVI-syn2.0"},
    "jcvi-syn2":   {"accession": "CP014992.1", "name": "Synthetic Mycoplasma mycoides JCVI-syn2.0"},
    "syn2.0":      {"accession": "CP014992.1", "name": "Synthetic Mycoplasma mycoides JCVI-syn2.0"},
    "jcvi-syn3.0": {"accession": "CP014940.1", "name": "Synthetic Mycoplasma mycoides JCVI-syn3.0"},
    "jcvi-syn3":   {"accession": "CP014940.1", "name": "Synthetic Mycoplasma mycoides JCVI-syn3.0"},
    "syn3.0":      {"accession": "CP014940.1", "name": "Synthetic Mycoplasma mycoides JCVI-syn3.0"},
    "jcvi-syn3a":  {"accession": "CP016816.2", "name": "Synthetic Mycoplasma mycoides JCVI-syn3A"},
    "syn3a":       {"accession": "CP016816.2", "name": "Synthetic Mycoplasma mycoides JCVI-syn3A"},
}

# Keywords that indicate a gene function is unknown
HYPOTHETICAL_KEYWORDS = {
    "hypothetical protein",
    "uncharacterized protein",
    "putative uncharacterized",
    "protein of unknown function",
    "duf",
    "unknown function",
    "predicted protein",
}

# Category inference from product annotations
CATEGORY_KEYWORDS: dict[FunctionalCategory, list[str]] = {
    FunctionalCategory.GENE_EXPRESSION: [
        "ribosom", "trna", "rrna", "polymerase", "sigma factor", "translation",
        "transcription", "elongation factor", "initiation factor", "release factor",
        "aminoacyl", "synthetase", "helicase rna", "rnase", "peptide chain",
    ],
    FunctionalCategory.CELL_MEMBRANE: [
        "membrane", "lipoprotein", "transporter", "permease", "abc transporter",
        "channel", "porin", "lipid", "phospholipid", "glycerol", "cardiolipin",
        "fatty acid", "acyl", "efflux", "import",
    ],
    FunctionalCategory.METABOLISM: [
        "kinase", "phosphatase", "dehydrogenase", "synthase", "reductase",
        "transferase", "isomerase", "ligase", "hydrolase", "oxidase",
        "protease", "peptidase", "nuclease", "enolase", "aldolase",
        "thioredoxin", "ferredoxin", "nadh", "atp synthase",
    ],
    FunctionalCategory.GENOME_PRESERVATION: [
        "dnaa", "dna polymerase", "dna gyrase", "topoisomerase", "recombinase",
        "repair", "recombination", "ssb", "ligase dna", "primase",
        "chromosome", "segregation", "partition", "ftsz", "cell division",
        "gyrb", "gyra", "topolog", "smc", "pare", "seqa",
    ],
}

# Colors for visualization
CATEGORY_COLORS: dict[FunctionalCategory, str] = {
    FunctionalCategory.GENE_EXPRESSION: "#22d3ee",     # cyan
    FunctionalCategory.CELL_MEMBRANE: "#a78bfa",        # purple
    FunctionalCategory.METABOLISM: "#34d399",            # green
    FunctionalCategory.GENOME_PRESERVATION: "#60a5fa",   # blue
    FunctionalCategory.PREDICTED: "#fb923c",             # orange
    FunctionalCategory.UNKNOWN: "#f87171",               # red
}


def _classify_gene(product: str, gene_name: str) -> tuple[FunctionalCategory, bool]:
    """Classify a gene by its product annotation."""
    text = f"{product} {gene_name}".lower()

    # Check if hypothetical
    is_hypo = any(kw in text for kw in HYPOTHETICAL_KEYWORDS)
    if is_hypo and not gene_name:
        return FunctionalCategory.UNKNOWN, True

    # Try to match a category
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category, is_hypo

    # Has a gene name or a non-hypothetical product — it's at least predicted
    if gene_name and not is_hypo:
        return FunctionalCategory.PREDICTED, False

    # Has a product description that isn't "hypothetical" — some function known
    if product and not is_hypo and len(product) > 10:
        return FunctionalCategory.PREDICTED, False

    if is_hypo:
        return FunctionalCategory.UNKNOWN, True

    return FunctionalCategory.UNKNOWN, False


def resolve_synthetic_name(query: str) -> str | None:
    """Resolve a synthetic organism name to a GenBank accession."""
    key = query.lower().strip().replace(" ", "").replace("_", "-")
    entry = SYNTHETIC_GENOMES.get(key)
    return entry["accession"] if entry else None


def get_synthetic_name(query: str) -> str:
    """Get the display name for a synthetic organism."""
    key = query.lower().strip().replace(" ", "").replace("_", "-")
    entry = SYNTHETIC_GENOMES.get(key)
    return entry["name"] if entry else query


async def fetch_genome_genbank(http: httpx.AsyncClient, accession: str) -> str:
    """Fetch a full GenBank record from NCBI."""
    base = config.ncbi.base_url
    params: dict[str, str] = {
        "db": "nucleotide",
        "id": accession,
        "rettype": "gb",
        "retmode": "text",
    }
    if config.ncbi.api_key:
        params["api_key"] = config.ncbi.api_key

    resp = await http.get(f"{base}/efetch.fcgi", params=params, timeout=60.0)
    resp.raise_for_status()
    return resp.text


def parse_genome(genbank_text: str, organism_override: str = "") -> GenomeRecord:
    """Parse a GenBank genome record into a GenomeRecord with all genes."""
    handle = io.StringIO(genbank_text)
    records = list(SeqIO.parse(handle, "genbank"))
    if not records:
        return GenomeRecord()

    rec = records[0]
    genome_seq = str(rec.seq)

    genome = GenomeRecord(
        accession=rec.id,
        organism=organism_override or rec.annotations.get("organism", ""),
        description=rec.description,
        genome_length=len(genome_seq),
        is_circular="circular" in rec.annotations.get("topology", ""),
    )

    # GC content
    gc = (genome_seq.count("G") + genome_seq.count("C")) / len(genome_seq) * 100
    genome.gc_content = round(gc, 2)

    # Extract all CDS features
    for feature in rec.features:
        if feature.type != "CDS":
            continue

        locus_tag = feature.qualifiers.get("locus_tag", [""])[0]
        product = feature.qualifiers.get("product", [""])[0]
        gene_name = feature.qualifiers.get("gene", [""])[0]
        protein_seq = feature.qualifiers.get("translation", [""])[0]

        if not locus_tag and not gene_name:
            continue

        start = int(feature.location.start)
        end = int(feature.location.end)
        strand = feature.location.strand or 1

        # Extract DNA sequence
        dna_seq = str(rec.seq[start:end])
        if strand == -1:
            dna_seq = str(rec.seq[start:end].reverse_complement())

        category, is_hypo = _classify_gene(product, gene_name)

        gene = GenomeGene(
            locus_tag=locus_tag or gene_name,
            product=product,
            gene_name=gene_name,
            start=start,
            end=end,
            strand=strand,
            dna_sequence=dna_seq,
            protein_sequence=protein_seq,
            protein_length=len(protein_seq),
            functional_category=category,
            is_hypothetical=is_hypo,
            color=CATEGORY_COLORS.get(category, "#888888"),
            prediction_source="genbank" if category != FunctionalCategory.UNKNOWN else "",
        )
        genome.genes.append(gene)

    genome.total_genes = len(genome.genes)
    genome.genes_known = sum(
        1 for g in genome.genes
        if g.functional_category not in (FunctionalCategory.UNKNOWN, FunctionalCategory.PREDICTED)
    )
    genome.genes_predicted = sum(
        1 for g in genome.genes if g.functional_category == FunctionalCategory.PREDICTED
    )
    genome.genes_unknown = sum(
        1 for g in genome.genes if g.functional_category == FunctionalCategory.UNKNOWN
    )

    return genome
