"""SynWiki literature source — fetches curated annotations from SynWiki MediaWiki.

Queries the SynWiki API at uni-goettingen.de for gene pages,
parses wikitext template fields for function, category, localization, GO, EC.
"""

from __future__ import annotations

import logging
import re

import httpx
from sqlalchemy.orm import Session

from openlab.db.models.gene import Gene
from openlab.pipeline.evidence_runner import has_existing_evidence
from openlab.registry import evidence_type_for
from openlab.services import evidence_service

logger = logging.getLogger(__name__)

SYNWIKI_API = "https://synwiki.uni-goettingen.de/api.php"


async def search_synwiki(http: httpx.AsyncClient, locus_tag: str) -> dict:
    """Fetch SynWiki page for a locus tag and parse template fields."""
    if not locus_tag:
        return {"source": "synwiki"}

    try:
        resp = await http.get(
            SYNWIKI_API,
            params={
                "action": "parse",
                "page": locus_tag,
                "prop": "wikitext",
                "format": "json",
            },
            timeout=15.0,
        )
        if resp.status_code != 200:
            return {"source": "synwiki"}

        data = resp.json()
        if "error" in data:
            return {"source": "synwiki"}

        wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")
        if not wikitext:
            return {"source": "synwiki"}

        return _parse_wikitext(wikitext)

    except Exception as e:
        logger.debug("SynWiki lookup failed for %s: %s", locus_tag, e)
        return {"source": "synwiki"}


def _parse_wikitext(wikitext: str) -> dict:
    """Extract structured fields from SynWiki template wikitext."""
    result: dict = {"source": "synwiki"}

    field_map = {
        "function": "function",
        "category": "category",
        "localization": "localization",
        "go_terms": "go_terms",
        "ec_number": "ec_number",
        "gene_name": "gene_name",
        "essential": "essential",
        "comment": "comment",
        "references": "references",
    }

    for wiki_field, key in field_map.items():
        pattern = rf"\|\s*{wiki_field}\s*=\s*(.+?)(?:\n\||\n\}}|$)"
        match = re.search(pattern, wikitext, re.IGNORECASE | re.DOTALL)
        if match:
            value = match.group(1).strip()
            if value and value != "-" and value.lower() != "unknown":
                result[key] = value

    # Parse GO terms into structured list
    if "go_terms" in result:
        go_raw = result["go_terms"]
        go_list = re.findall(r"(GO:\d+)", go_raw)
        if go_list:
            result["go_terms"] = go_list

    # Parse EC number
    if "ec_number" in result:
        ec_match = re.findall(r"(\d+\.\d+\.\d+\.\d+)", result["ec_number"])
        if ec_match:
            result["ec_number"] = ec_match

    return result


def run_synwiki(db: Session, genes: list[Gene], http: httpx.Client) -> int:
    """Batch runner: fetch SynWiki annotations for each gene."""
    count = 0
    for gene in genes:
        if has_existing_evidence(db, gene.gene_id, "synwiki"):
            continue
        if not gene.locus_tag:
            continue

        try:
            resp = http.get(
                SYNWIKI_API,
                params={
                    "action": "parse",
                    "page": gene.locus_tag,
                    "prop": "wikitext",
                    "format": "json",
                },
                timeout=15.0,
            )
            if resp.status_code != 200:
                continue

            data = resp.json()
            if "error" in data:
                continue

            wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")
            if not wikitext:
                continue

            result = _parse_wikitext(wikitext)
            # Only store if we got meaningful content
            if len(result) <= 1:  # just "source"
                continue

            result["source"] = "SynWiki"
            evidence_service.add_evidence(
                db,
                gene_id=gene.gene_id,
                evidence_type=evidence_type_for("synwiki"),
                payload=result,
                source_ref="synwiki",
                confidence=0.7,
            )
            count += 1
            logger.info("SynWiki %s: %s", gene.locus_tag,
                        result.get("function", "no function field"))

        except Exception as e:
            logger.warning("SynWiki %s error: %s", gene.locus_tag, e)

    return count
