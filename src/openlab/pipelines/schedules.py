"""Dagster schedules for periodic pipeline runs."""

from dagster import ScheduleDefinition, define_asset_job

from openlab.pipelines.assets.context import literature_search, eggnog_annotations
from openlab.pipelines.assets.synthesis import llm_hypothesis_synthesis

# Full pipeline: all evidence sources + synthesis
full_pipeline_job = define_asset_job(
    name="full_pipeline",
    description="Run all evidence collection sources and LLM synthesis",
)

# Literature-only refresh
literature_refresh_job = define_asset_job(
    name="literature_refresh",
    selection=[literature_search],
    description="Refresh literature evidence from EuropePMC",
)

# Synthesis-only refresh
synthesis_refresh_job = define_asset_job(
    name="synthesis_refresh",
    selection=[llm_hypothesis_synthesis],
    description="Re-run LLM synthesis on genes with new evidence",
)

weekly_full_pipeline = ScheduleDefinition(
    job=full_pipeline_job,
    cron_schedule="0 2 * * 0",  # Sunday 2 AM
    description="Weekly full evidence collection pipeline",
)

daily_literature_refresh = ScheduleDefinition(
    job=literature_refresh_job,
    cron_schedule="0 6 * * *",  # Daily 6 AM
    description="Daily literature refresh from EuropePMC",
)

daily_synthesis_refresh = ScheduleDefinition(
    job=synthesis_refresh_job,
    cron_schedule="0 8 * * *",  # Daily 8 AM
    description="Daily LLM synthesis for genes with new evidence",
)
