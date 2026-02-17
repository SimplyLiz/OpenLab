"""Dagster assets: contextual evidence sources."""

from dagster import asset, AssetExecutionContext

from openlab.pipelines.resources import DatabaseResource, HttpClientResource


@asset(group_name="evidence", kinds={"api"})
def string_interactions(context: AssetExecutionContext, database: DatabaseResource, http_client: HttpClientResource):
    """STRING DB protein interaction network (existing source)."""
    context.log.info("STRING runs via pipeline orchestrator")
    return 0


@asset(group_name="evidence", kinds={"api"})
def literature_search(context: AssetExecutionContext, database: DatabaseResource, http_client: HttpClientResource):
    """Enhanced EuropePMC literature search."""
    from openlab.pipeline.evidence_runner import run_source
    count = run_source("europepmc", unknown_only=True)
    context.log.info(f"EuropePMC: {count} literature results")
    return count


@asset(group_name="evidence", kinds={"api"})
def eggnog_annotations(context: AssetExecutionContext, database: DatabaseResource, http_client: HttpClientResource):
    """eggNOG-mapper functional annotation."""
    from openlab.pipeline.evidence_runner import run_source
    count = run_source("eggnog_online", unknown_only=True)
    context.log.info(f"eggNOG: {count} annotations")
    return count


@asset(group_name="evidence", kinds={"computation"})
def operon_predictions(context: AssetExecutionContext, database: DatabaseResource, http_client: HttpClientResource):
    """Operon prediction from genomic organization."""
    from openlab.pipeline.evidence_runner import run_source
    count = run_source("operon_prediction", unknown_only=True)
    context.log.info(f"Operons: {count} predictions")
    return count


@asset(group_name="evidence", kinds={"computation"})
def phylogenetic_profiles(context: AssetExecutionContext, database: DatabaseResource, http_client: HttpClientResource):
    """Phylogenetic profiling via DIAMOND BLAST."""
    from openlab.pipeline.evidence_runner import run_source
    count = run_source("phylogenetic_profile", unknown_only=True)
    context.log.info(f"Phylogenetic profiles: {count}")
    return count
