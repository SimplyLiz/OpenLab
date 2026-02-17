"""Dagster asset: SynWiki curated annotations."""

from dagster import asset, AssetExecutionContext

from openlab.pipelines.resources import DatabaseResource, HttpClientResource


@asset(group_name="evidence", kinds={"api"})
def synwiki_annotations(context: AssetExecutionContext, database: DatabaseResource, http_client: HttpClientResource):
    """SynWiki curated gene annotations from uni-goettingen.de."""
    from openlab.pipeline.evidence_runner import run_source
    count = run_source("synwiki", unknown_only=True)
    context.log.info(f"SynWiki: {count} annotations")
    return count
