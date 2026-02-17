"""Dagster assets: local homology search tools (HHblits, PROST)."""

from dagster import asset, AssetExecutionContext

from openlab.pipelines.resources import DatabaseResource, HttpClientResource


@asset(group_name="evidence", kinds={"tool"})
def hhblits_search(context: AssetExecutionContext, database: DatabaseResource, http_client: HttpClientResource):
    """HHblits local profile-profile search."""
    from openlab.pipeline.evidence_runner import run_source
    count = run_source("hhblits", unknown_only=True)
    context.log.info(f"HHblits: {count} homology results")
    return count


@asset(group_name="evidence", kinds={"tool"})
def prost_search(context: AssetExecutionContext, database: DatabaseResource, http_client: HttpClientResource):
    """PROST structure-based homology transfer."""
    from openlab.pipeline.evidence_runner import run_source
    count = run_source("prost", unknown_only=True)
    context.log.info(f"PROST: {count} homology results")
    return count
