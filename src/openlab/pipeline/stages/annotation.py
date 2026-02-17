"""Stage 3: Annotation — pull everything known about this gene.

GO terms, disease associations, pathways, drug targets, PubMed count.
Data sources: UniProt (primary), NCBI (supplementary), Ensembl (GO terms).
"""

from __future__ import annotations

import httpx

from openlab.models import (
    AnnotationResult, DiseaseAssociation, DrugTarget, GOTerm,
    GeneRecord, Pathway,
)
from openlab.services import ensembl, ncbi, uniprot


async def run(record: GeneRecord, http: httpx.AsyncClient) -> AnnotationResult:
    """Run annotation stage."""
    result = AnnotationResult()
    ids = record.identifiers

    # ------------------------------------------------------------------
    # UniProt — richest source of curated functional annotation
    # ------------------------------------------------------------------
    uni_entry = None
    if ids.uniprot_id:
        try:
            uni_entry = await uniprot.get_entry(http, ids.uniprot_id)
        except Exception:
            pass
    elif ids.symbol:
        try:
            uni_entry = await uniprot.search_by_gene(http, ids.symbol)
        except Exception:
            pass

    if uni_entry:
        # GO terms
        raw_go = uniprot.extract_go_terms(uni_entry)
        result.go_terms = [
            GOTerm(
                go_id=g["go_id"], name=g["name"],
                category=g.get("category", ""), evidence=g.get("evidence", ""),
            )
            for g in raw_go
        ]

        # Disease associations
        raw_diseases = uniprot.extract_diseases(uni_entry)
        result.diseases = [
            DiseaseAssociation(
                disease=d["disease"], source=d["source"],
                mim_id=d.get("mim_id", ""),
            )
            for d in raw_diseases
        ]

        # Function summary
        result.function_summary = uniprot.extract_function_summary(uni_entry)

        # Pathways
        raw_pathways = uniprot.extract_pathways(uni_entry)
        result.pathways = [
            Pathway(
                pathway_id=p["pathway_id"], name=p["name"], source=p["source"],
            )
            for p in raw_pathways
        ]

        # Drug targets from UniProt comments
        for comment in uni_entry.get("comments", []):
            if comment.get("commentType") == "PHARMACEUTICAL":
                texts = comment.get("texts", [])
                if texts:
                    result.drugs.append(DrugTarget(
                        drug_name=texts[0].get("value", "unknown"),
                        action="pharmaceutical_target",
                    ))

    # ------------------------------------------------------------------
    # Supplement GO terms from Ensembl if we got few from UniProt
    # ------------------------------------------------------------------
    if len(result.go_terms) < 5 and ids.ensembl_gene:
        try:
            ens_go = await ensembl.get_go_terms(http, ids.ensembl_gene)
            existing_ids = {g.go_id for g in result.go_terms}
            for g in ens_go:
                if g["go_id"] not in existing_ids:
                    result.go_terms.append(GOTerm(
                        go_id=g["go_id"], name=g["name"],
                        category="", evidence=g.get("evidence", ""),
                    ))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # PubMed citation count
    # ------------------------------------------------------------------
    if ids.symbol:
        try:
            result.pubmed_count = await ncbi.get_pubmed_count(http, ids.symbol)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # OMIM links via NCBI
    # ------------------------------------------------------------------
    if ids.ncbi_gene_id and not result.diseases:
        try:
            omim_ids = await ncbi.get_gene_links(http, ids.ncbi_gene_id, "omim")
            for mid in omim_ids[:10]:
                result.diseases.append(DiseaseAssociation(
                    disease=f"OMIM:{mid}", source="OMIM", mim_id=mid,
                ))
        except Exception:
            pass

    return result
