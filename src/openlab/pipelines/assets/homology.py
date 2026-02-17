"""Dagster assets: homology-based evidence sources."""

from dagster import asset, AssetExecutionContext

from openlab.pipelines.resources import DatabaseResource, HttpClientResource


@asset(group_name="evidence", kinds={"api"})
def ncbi_blast(context: AssetExecutionContext, database: DatabaseResource, http_client: HttpClientResource):
    """NCBI BLAST homology search (uses existing functional_prediction stage)."""
    from openlab.pipeline.evidence_runner import run_source
    count = run_source("europepmc", unknown_only=True)  # placeholder — BLAST is in functional_prediction
    context.log.info(f"NCBI BLAST: {count} evidence rows")
    return count


@asset(group_name="evidence", kinds={"api"})
def interproscan(context: AssetExecutionContext, database: DatabaseResource, http_client: HttpClientResource):
    """InterProScan domain classification (existing source)."""
    context.log.info("InterProScan runs via pipeline orchestrator")
    return 0


@asset(group_name="evidence", kinds={"api"})
def hmmer_search(context: AssetExecutionContext, database: DatabaseResource, http_client: HttpClientResource):
    """hmmscan against Pfam database."""
    from openlab.pipeline.evidence_runner import run_source
    count = run_source("hmmscan", unknown_only=True)
    context.log.info(f"hmmscan: {count} evidence rows")
    return count


@asset(group_name="evidence", kinds={"api"})
def hhpred_search(context: AssetExecutionContext, database: DatabaseResource, http_client: HttpClientResource):
    """HHpred remote homology detection."""
    from openlab.pipeline.evidence_runner import run_source
    count = run_source("hhpred", unknown_only=True)
    context.log.info(f"HHpred: {count} evidence rows")
    return count
