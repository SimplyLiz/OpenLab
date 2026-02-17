"""Enhanced EuropePMC literature search.

Extends the basic literature search with DNASyn's query strategy:
- Primary queries: gene name + mycoplasma, product + mycoplasma, locus_tag
- Fallback queries: core syn3A papers if no primary hits
- resultType: "core" (not "lite") for full abstracts
"""

from __future__ import annotations

import logging

import httpx
from sqlalchemy.orm import Session

from openlab.db.models.gene import Gene
from openlab.pipeline.evidence_runner import has_existing_evidence
from openlab.registry import evidence_type_for
from openlab.services import evidence_service

logger = logging.getLogger(__name__)

EUROPEPMC_API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

# Core syn3A / JCVI-syn papers — always relevant as fallback
CORE_SYN3A_QUERIES = [
    '"JCVI-syn3.0" OR "JCVI-syn3A"',
    '"minimal bacterial genome" AND "mycoplasma"',
    '"essential genes" AND "mycoplasma mycoides"',
]


async def search_europepmc(
    http: httpx.AsyncClient,
    gene_name: str = "",
    product: str = "",
    locus_tag: str = "",
) -> dict:
    """Enhanced EuropePMC search with DNASyn query strategy."""
    primary_queries = _build_primary_queries(gene_name, product, locus_tag)
    if not primary_queries:
        return {"source": "europepmc"}

    all_articles = []
    total_hits = 0

    try:
        for query in primary_queries:
            articles, hits = await _run_query(http, query)
            all_articles.extend(articles)
            total_hits += hits
            if all_articles:
                break  # Got results, skip remaining primary queries

        # Fallback to core syn3A papers if nothing found
        if not all_articles and locus_tag:
            for query in CORE_SYN3A_QUERIES:
                articles, hits = await _run_query(http, query, page_size=3)
                all_articles.extend(articles)
                total_hits += hits
                if all_articles:
                    break

        # Deduplicate by PMID
        seen = set()
        unique = []
        for article in all_articles:
            pmid = article.get("pmid", "")
            if pmid and pmid in seen:
                continue
            seen.add(pmid)
            unique.append(article)

        return {
            "source": "europepmc",
            "articles": unique[:10],
            "total_hits": total_hits,
            "query_used": primary_queries[0] if primary_queries else "",
        }

    except Exception as e:
        logger.debug("EuropePMC search failed: %s", e)
        return {"source": "europepmc"}


def _build_primary_queries(gene_name: str, product: str, locus_tag: str) -> list[str]:
    """Build prioritized list of search queries."""
    queries = []

    if gene_name and gene_name.lower() != "unknown":
        queries.append(f'("{gene_name}" AND (mycoplasma OR "JCVI-syn" OR "minimal genome"))')

    if product and "hypothetical" not in product.lower() and "uncharacterized" not in product.lower():
        queries.append(f'("{product}" AND (mycoplasma OR "JCVI-syn" OR "minimal genome"))')

    if locus_tag:
        queries.append(f'"{locus_tag}"')

    return queries


async def _run_query(
    http: httpx.AsyncClient,
    query: str,
    page_size: int = 5,
) -> tuple[list[dict], int]:
    """Execute a single EuropePMC query, return (articles, total_hits)."""
    try:
        resp = await http.get(
            EUROPEPMC_API,
            params={
                "query": query,
                "resultType": "core",
                "pageSize": str(page_size),
                "format": "json",
            },
            timeout=15.0,
        )
        if resp.status_code != 200:
            return [], 0

        data = resp.json()
        articles = []
        for result in data.get("resultList", {}).get("result", []):
            articles.append({
                "title": result.get("title", ""),
                "abstract": result.get("abstractText", ""),
                "authors": result.get("authorString", ""),
                "journal": result.get("journalTitle", ""),
                "year": result.get("pubYear", ""),
                "pmid": result.get("pmid", ""),
                "doi": result.get("doi", ""),
                "cited_by": result.get("citedByCount", 0),
            })

        return articles, data.get("hitCount", 0)
    except Exception:
        return [], 0


def run_europepmc(db: Session, genes: list[Gene], http: httpx.Client) -> int:
    """Batch runner: search EuropePMC for literature on each gene."""
    count = 0
    for gene in genes:
        if has_existing_evidence(db, gene.gene_id, "europepmc"):
            continue

        primary_queries = _build_primary_queries(
            gene.name or "", gene.product or "", gene.locus_tag
        )
        if not primary_queries:
            continue

        try:
            all_articles = []
            total_hits = 0

            for query in primary_queries:
                resp = http.get(
                    EUROPEPMC_API,
                    params={
                        "query": query,
                        "resultType": "core",
                        "pageSize": "5",
                        "format": "json",
                    },
                    timeout=15.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    total_hits += data.get("hitCount", 0)
                    for result in data.get("resultList", {}).get("result", []):
                        all_articles.append({
                            "title": result.get("title", ""),
                            "abstract": result.get("abstractText", ""),
                            "authors": result.get("authorString", ""),
                            "journal": result.get("journalTitle", ""),
                            "year": result.get("pubYear", ""),
                            "pmid": result.get("pmid", ""),
                            "doi": result.get("doi", ""),
                            "cited_by": result.get("citedByCount", 0),
                        })
                    if all_articles:
                        break

            # Fallback
            if not all_articles:
                for query in CORE_SYN3A_QUERIES:
                    resp = http.get(
                        EUROPEPMC_API,
                        params={
                            "query": query,
                            "resultType": "core",
                            "pageSize": "3",
                            "format": "json",
                        },
                        timeout=15.0,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for result in data.get("resultList", {}).get("result", []):
                            all_articles.append({
                                "title": result.get("title", ""),
                                "abstract": result.get("abstractText", ""),
                                "authors": result.get("authorString", ""),
                                "journal": result.get("journalTitle", ""),
                                "year": result.get("pubYear", ""),
                                "pmid": result.get("pmid", ""),
                                "doi": result.get("doi", ""),
                                "cited_by": result.get("citedByCount", 0),
                            })
                        if all_articles:
                            break

            if not all_articles:
                continue

            # Deduplicate
            seen = set()
            unique = []
            for article in all_articles:
                pmid = article.get("pmid", "")
                if pmid and pmid in seen:
                    continue
                seen.add(pmid)
                unique.append(article)

            evidence_service.add_evidence(
                db,
                gene_id=gene.gene_id,
                evidence_type=evidence_type_for("europepmc"),
                payload={
                    "source": "EuropePMC",
                    "articles": unique[:10],
                    "total_hits": total_hits,
                },
                source_ref="europepmc",
                confidence=0.5,
            )
            count += 1
            logger.info("EuropePMC %s: %d articles (total hits=%d)",
                        gene.locus_tag, len(unique), total_hits)

        except Exception as e:
            logger.warning("EuropePMC %s error: %s", gene.locus_tag, e)

    return count
