"""Dagster assets: structure prediction and structural similarity."""

from dagster import asset, AssetExecutionContext

from openlab.pipelines.resources import DatabaseResource, HttpClientResource


@asset(group_name="evidence", kinds={"api"})
def esmfold_structures(context: AssetExecutionContext, database: DatabaseResource, http_client: HttpClientResource):
    """ESMFold structure prediction via HuggingFace API."""
    from openlab.pipeline.evidence_runner import run_source
    count = run_source("esmfold", unknown_only=True)
    context.log.info(f"ESMFold: {count} structures predicted")
    return count


@asset(group_name="evidence", kinds={"api"}, deps=[esmfold_structures])
def alphafold_structures(context: AssetExecutionContext, database: DatabaseResource, http_client: HttpClientResource):
    """AlphaFold DB structure retrieval."""
    from openlab.pipeline.evidence_runner import run_source
    count = run_source("alphafold", unknown_only=True)
    context.log.info(f"AlphaFold: {count} structures retrieved")
    return count


@asset(group_name="evidence", kinds={"api"}, deps=[esmfold_structures, alphafold_structures])
def foldseek_search(context: AssetExecutionContext, database: DatabaseResource, http_client: HttpClientResource):
    """Foldseek online structural similarity search."""
    from openlab.pipeline.evidence_runner import run_source
    count = run_source("foldseek", unknown_only=True)
    context.log.info(f"Foldseek: {count} search results")
    return count
