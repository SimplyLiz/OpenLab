"""Stage 1: Ingest — resolve gene input to a complete GeneRecord or GenomeRecord.

Accepts gene symbol, NCBI accession, Ensembl ID, UniProt ID, raw FASTA,
GenBank genome accession, or synthetic organism name (e.g. JCVI-syn3.0).
"""

from __future__ import annotations

import re

import httpx

from openlab.models import (
    GeneIdentifiers, GeneInput, GeneRecord, GenomeRecord, InputType, Sequence,
)
from openlab.services import ensembl, genbank, ncbi, uniprot


def detect_input_type(query: str) -> InputType:
    """Auto-detect the type of gene input."""
    q = query.strip()
    if q.startswith(">") or re.match(r"^[ATCGNatcgn\s]{20,}$", q):
        return InputType.FASTA
    if re.match(r"^[NX][MR]_\d+", q):
        return InputType.NCBI_ACCESSION
    if re.match(r"^ENSG\d{11}", q):
        return InputType.ENSEMBL_ID
    if re.match(r"^[A-Z]\d[A-Z0-9]{3}\d$", q):  # UniProt accession pattern
        return InputType.UNIPROT_ID
    # GenBank genome accession (e.g. CP014992.1)
    if re.match(r"^CP\d{6}", q) or re.match(r"^[A-Z]{2}_?\d{6,}", q):
        return InputType.GENBANK_GENOME
    # Synthetic organism names
    if genbank.resolve_synthetic_name(q):
        return InputType.SYNTHETIC
    return InputType.SYMBOL


def _parse_fasta(text: str) -> str:
    """Extract raw sequence from FASTA format."""
    lines = text.strip().split("\n")
    seq_lines = [l.strip() for l in lines if not l.startswith(">")]
    return "".join(seq_lines).upper()


async def run_genome(gene_input: GeneInput, http: httpx.AsyncClient) -> GenomeRecord:
    """Ingest a whole genome (synthetic organism or GenBank accession)."""
    query = gene_input.query.strip()
    input_type = gene_input.input_type or detect_input_type(query)

    accession = ""
    organism_name = ""

    if input_type == InputType.SYNTHETIC:
        accession = genbank.resolve_synthetic_name(query) or ""
        organism_name = genbank.get_synthetic_name(query)
    elif input_type == InputType.GENBANK_GENOME:
        accession = query

    if not accession:
        return GenomeRecord(description=f"Could not resolve: {query}")

    gb_text = await genbank.fetch_genome_genbank(http, accession)
    genome = genbank.parse_genome(gb_text, organism_override=organism_name)
    return genome


def is_genome_query(gene_input: GeneInput) -> bool:
    """Check if this input should be handled as a whole genome."""
    q = gene_input.query.strip()
    if gene_input.input_type in (InputType.GENBANK_GENOME, InputType.SYNTHETIC):
        return True
    detected = detect_input_type(q)
    return detected in (InputType.GENBANK_GENOME, InputType.SYNTHETIC)


async def run(gene_input: GeneInput, http: httpx.AsyncClient) -> GeneRecord:
    """Execute the ingest stage (single gene mode)."""
    query = gene_input.query.strip()
    input_type = gene_input.input_type or detect_input_type(query)

    record = GeneRecord()

    if input_type == InputType.FASTA:
        seq = _parse_fasta(query)
        record.sequences.append(
            Sequence(seq_type="unknown", sequence=seq, length=len(seq))
        )
        record.identifiers.symbol = "user_sequence"
        return record

    # -----------------------------------------------------------------------
    # Resolve via NCBI Gene
    # -----------------------------------------------------------------------
    gene_id: str | None = None

    if input_type == InputType.SYMBOL:
        gene_id = await ncbi.search_gene(http, query)

    elif input_type == InputType.NCBI_ACCESSION:
        # Search for gene linked to this accession
        gene_id = await ncbi.search_gene(http, query)

    elif input_type == InputType.ENSEMBL_ID:
        # Get gene info from Ensembl, then cross-ref to NCBI
        ens_data = await ensembl.get_gene(http, query)
        if ens_data:
            symbol = ens_data.get("display_name", "")
            record.identifiers.ensembl_gene = query
            record.identifiers.symbol = symbol
            if symbol:
                gene_id = await ncbi.search_gene(http, symbol)

    elif input_type == InputType.UNIPROT_ID:
        entry = await uniprot.get_entry(http, query)
        genes = entry.get("genes", [{}])
        symbol = genes[0].get("geneName", {}).get("value", "") if genes else ""
        record.identifiers.uniprot_id = query
        record.identifiers.symbol = symbol
        if symbol:
            gene_id = await ncbi.search_gene(http, symbol)

    # -----------------------------------------------------------------------
    # Fetch full gene info from NCBI
    # -----------------------------------------------------------------------
    if gene_id:
        info = await ncbi.get_gene_info(http, gene_id)
        record.identifiers = GeneIdentifiers(
            symbol=info.get("symbol", query),
            name=info.get("name", ""),
            ncbi_gene_id=gene_id,
            refseq_mrna=info.get("refseq_mrna", ""),
            refseq_protein=info.get("refseq_protein", ""),
            organism=info.get("organism", "Homo sapiens"),
            map_location=info.get("map_location", ""),
        )
        record.summary = info.get("summary", "")
        record.aliases = info.get("aliases", [])

    # -----------------------------------------------------------------------
    # Cross-reference with Ensembl
    # -----------------------------------------------------------------------
    if record.identifiers.symbol and not record.identifiers.ensembl_gene:
        ens_data = await ensembl.lookup_symbol(http, record.identifiers.symbol)
        if ens_data:
            record.identifiers.ensembl_gene = ens_data.get("id", "")
            record.identifiers.chromosome = str(ens_data.get("seq_region_name", ""))

            # Get UniProt xref if not already set
            if not record.identifiers.uniprot_id:
                xrefs = await ensembl.get_xrefs(
                    http, record.identifiers.ensembl_gene, "UniProt/SWISSPROT"
                )
                if xrefs:
                    record.identifiers.uniprot_id = xrefs[0].get("primary_id", "")

    # -----------------------------------------------------------------------
    # Fetch sequences
    # -----------------------------------------------------------------------
    if record.identifiers.refseq_mrna:
        try:
            fasta = await ncbi.fetch_sequence(http, record.identifiers.refseq_mrna)
            seq = _parse_fasta(fasta)
            record.sequences.append(Sequence(
                accession=record.identifiers.refseq_mrna,
                seq_type="mrna", sequence=seq, length=len(seq),
            ))
        except Exception:
            pass

    if record.identifiers.refseq_protein:
        try:
            fasta = await ncbi.fetch_protein_sequence(http, record.identifiers.refseq_protein)
            seq = _parse_fasta(fasta)
            record.sequences.append(Sequence(
                accession=record.identifiers.refseq_protein,
                seq_type="protein", sequence=seq, length=len(seq),
            ))
        except Exception:
            pass

    # Fetch CDS via Ensembl if we have the gene ID
    if record.identifiers.ensembl_gene:
        try:
            cds = await ensembl.get_sequence(http, record.identifiers.ensembl_gene, "cds")
            if cds:
                record.sequences.append(Sequence(
                    accession=record.identifiers.ensembl_gene,
                    seq_type="cds", sequence=cds, length=len(cds),
                ))
        except Exception:
            pass

    return record
