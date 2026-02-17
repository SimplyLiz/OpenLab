"""Dagster sensors for reactive pipeline triggers."""

from dagster import RunRequest, SensorEvaluationContext, sensor, define_asset_job

from openlab.pipelines.assets.synthesis import llm_hypothesis_synthesis


@sensor(
    description="Detect newly imported genes that need evidence collection",
    minimum_interval_seconds=300,
)
def new_genes_sensor(context: SensorEvaluationContext):
    """Trigger pipeline when new genes without evidence are detected."""
    from openlab.db.engine import get_session_factory
    from openlab.services.gene_service import genes_without_evidence

    factory = get_session_factory()
    with factory() as db:
        new_genes = genes_without_evidence(db)

    if new_genes:
        context.log.info(f"Found {len(new_genes)} genes without evidence")
        yield RunRequest(
            run_key=f"new_genes_{len(new_genes)}",
            tags={"trigger": "new_genes", "gene_count": str(len(new_genes))},
        )


@sensor(
    description="Detect genes with stale evidence that needs refreshing",
    minimum_interval_seconds=3600,
)
def stale_evidence_sensor(context: SensorEvaluationContext):
    """Trigger re-collection when evidence is older than configured max age."""
    from openlab.config import config
    from openlab.db.engine import get_session_factory
    from openlab.services.gene_service import genes_with_stale_evidence

    factory = get_session_factory()
    with factory() as db:
        stale = genes_with_stale_evidence(db, max_age_days=config.pipeline.evidence_max_age_days)

    if stale:
        context.log.info(f"Found {len(stale)} genes with stale evidence")
        yield RunRequest(
            run_key=f"stale_{len(stale)}",
            tags={"trigger": "stale_evidence", "gene_count": str(len(stale))},
        )
