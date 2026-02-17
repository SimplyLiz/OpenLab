"""Dagster assets: protein localization prediction."""

from dagster import asset, AssetExecutionContext

from openlab.pipelines.resources import DatabaseResource, HttpClientResource


@asset(group_name="evidence", kinds={"tool"})
def deeptmhmm_topology(context: AssetExecutionContext, database: DatabaseResource, http_client: HttpClientResource):
    """DeepTMHMM transmembrane topology prediction."""
    from openlab.pipeline.evidence_runner import run_source
    count = run_source("deeptmhmm", unknown_only=True)
    context.log.info(f"DeepTMHMM: {count} topology predictions")
    return count


@asset(group_name="evidence", kinds={"tool"})
def signalp_predictions(context: AssetExecutionContext, database: DatabaseResource, http_client: HttpClientResource):
    """SignalP 6.0 signal peptide prediction."""
    from openlab.pipeline.evidence_runner import run_source
    count = run_source("signalp", unknown_only=True)
    context.log.info(f"SignalP: {count} signal peptide predictions")
    return count
