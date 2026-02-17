"""Pipeline orchestrator — runs analysis stages and streams results.

Two modes:
  Single gene: ingest → (sequence_analysis + annotation) in parallel
  Genome:      genome_ingest → prior_knowledge → functional_prediction
               → essentiality → kinetics → cellspec → simulation → validation
"""

from __future__ import annotations

import asyncio
import traceback
from collections.abc import AsyncGenerator

import httpx

from openlab.models import (
    CellSpec, FunctionalCategory, GeneInput, GeneRecord,
    GenomeRecord, PipelineEvent, StageStatus,
)
from openlab.pipeline.stages import (
    annotation, functional_prediction, ingest, sequence_analysis,
    essentiality_prediction, kinetics_enrichment, cellspec_assembly,
    simulation, validation,
)
from openlab.services.prior_knowledge import get_prior_knowledge


async def run_pipeline(
    gene_input: GeneInput,
    http: httpx.AsyncClient,
) -> AsyncGenerator[PipelineEvent, None]:
    """Run the full analysis pipeline, yielding events as stages complete."""

    # Detect if this is a genome query
    if ingest.is_genome_query(gene_input):
        async for event in _run_genome_pipeline(gene_input, http):
            yield event
        return

    # Otherwise, single gene mode
    async for event in _run_gene_pipeline(gene_input, http):
        yield event


async def _run_genome_pipeline(
    gene_input: GeneInput,
    http: httpx.AsyncClient,
) -> AsyncGenerator[PipelineEvent, None]:
    """Pipeline for whole genomes (synthetic organisms)."""

    # ------------------------------------------------------------------
    # Stage 1: Genome Ingest
    # ------------------------------------------------------------------
    yield PipelineEvent(
        stage="genome_ingest", status=StageStatus.RUNNING, progress=0.0,
        data={"message": f"Fetching genome: {gene_input.query}..."},
    )

    try:
        genome: GenomeRecord = await ingest.run_genome(gene_input, http)
        yield PipelineEvent(
            stage="genome_ingest",
            status=StageStatus.COMPLETED,
            progress=1.0,
            data=genome.model_dump(),
        )
    except Exception as e:
        yield PipelineEvent(
            stage="genome_ingest", status=StageStatus.FAILED,
            error=f"{type(e).__name__}: {e}\n{traceback.format_exc()}",
        )
        return

    # ------------------------------------------------------------------
    # Apply DNASyn prior knowledge — reclassify genes already figured out
    # ------------------------------------------------------------------
    prior = get_prior_knowledge()
    reclassified = 0
    for gene in genome.genes:
        pk = prior.get(gene.locus_tag)
        if pk and gene.functional_category == FunctionalCategory.UNKNOWN:
            gene.functional_category = FunctionalCategory.PREDICTED
            gene.product = pk.proposed_function
            gene.is_hypothetical = False
            # Curated = green-ish, DNASyn pipeline = orange
            is_curated = pk.source.startswith("curated:")
            gene.prediction_source = "curated" if is_curated else "dnasyn"
            gene.color = "#2dd4bf" if is_curated else "#fb923c"
            reclassified += 1

    if reclassified > 0:
        # Update genome counts
        genome.genes_unknown = sum(
            1 for g in genome.genes if g.functional_category == FunctionalCategory.UNKNOWN
        )
        genome.genes_predicted = sum(
            1 for g in genome.genes if g.functional_category == FunctionalCategory.PREDICTED
        )
        # Re-emit the updated genome so the UI reflects prior knowledge immediately
        yield PipelineEvent(
            stage="genome_ingest",
            status=StageStatus.COMPLETED,
            progress=1.0,
            data=genome.model_dump(),
        )

    # ------------------------------------------------------------------
    # Stage 2: Functional Prediction for remaining mystery genes
    # ------------------------------------------------------------------
    async for event in functional_prediction.run(genome, http):
        yield event

    # Yield the updated genome with predictions applied
    yield PipelineEvent(
        stage="genome_updated",
        status=StageStatus.COMPLETED,
        progress=1.0,
        data=genome.model_dump(),
    )

    # ------------------------------------------------------------------
    # Stage 3: Essentiality Prediction
    # ------------------------------------------------------------------
    try:
        async for event in essentiality_prediction.run(genome):
            yield event
    except Exception as e:
        yield PipelineEvent(
            stage="essentiality_prediction", status=StageStatus.FAILED,
            error=f"{type(e).__name__}: {e}",
        )

    # ------------------------------------------------------------------
    # Stage 4: Kinetics Enrichment
    # ------------------------------------------------------------------
    kinetics_data: list[dict] = []
    try:
        async for event in kinetics_enrichment.run(genome, http):
            yield event
            # Capture kinetics from completed event
            if event.status == StageStatus.COMPLETED and event.data:
                kinetics_data = event.data.get("kinetics", [])
    except Exception as e:
        yield PipelineEvent(
            stage="kinetics_enrichment", status=StageStatus.FAILED,
            error=f"{type(e).__name__}: {e}",
        )

    # ------------------------------------------------------------------
    # Stage 5: CellSpec Assembly
    # ------------------------------------------------------------------
    cellspec: CellSpec | None = None
    try:
        async for event in cellspec_assembly.run(genome, kinetics_data, http):
            yield event
            if event.status == StageStatus.COMPLETED and event.data:
                cellspec = CellSpec.model_validate(event.data)
    except Exception as e:
        yield PipelineEvent(
            stage="cellspec_assembly", status=StageStatus.FAILED,
            error=f"{type(e).__name__}: {e}",
        )

    if cellspec is None:
        return

    # ------------------------------------------------------------------
    # Stage 6: Simulation
    # ------------------------------------------------------------------
    sim_time_series: list[dict] = []
    sim_summary: dict = {}
    try:
        async for event in simulation.run(cellspec):
            yield event
            if event.status == StageStatus.COMPLETED and event.data:
                sim_time_series = event.data.get("time_series", [])
                sim_summary = event.data.get("summary", {})
    except Exception as e:
        yield PipelineEvent(
            stage="simulation", status=StageStatus.FAILED,
            error=f"{type(e).__name__}: {e}",
        )

    # ------------------------------------------------------------------
    # Stage 7: Validation
    # ------------------------------------------------------------------
    try:
        async for event in validation.run(cellspec, sim_time_series, sim_summary):
            yield event
    except Exception as e:
        yield PipelineEvent(
            stage="validation", status=StageStatus.FAILED,
            error=f"{type(e).__name__}: {e}",
        )


async def _run_gene_pipeline(
    gene_input: GeneInput,
    http: httpx.AsyncClient,
) -> AsyncGenerator[PipelineEvent, None]:
    """Pipeline for single gene analysis."""

    # ------------------------------------------------------------------
    # Stage 1: Ingest
    # ------------------------------------------------------------------
    yield PipelineEvent(stage="ingest", status=StageStatus.RUNNING, progress=0.0)

    try:
        record: GeneRecord = await ingest.run(gene_input, http)
        yield PipelineEvent(
            stage="ingest",
            status=StageStatus.COMPLETED,
            progress=1.0,
            data=record.model_dump(),
        )
    except Exception as e:
        yield PipelineEvent(
            stage="ingest", status=StageStatus.FAILED,
            error=f"{type(e).__name__}: {e}\n{traceback.format_exc()}",
        )
        return

    # ------------------------------------------------------------------
    # Stages 2 & 3: Sequence Analysis + Annotation (parallel)
    # ------------------------------------------------------------------
    yield PipelineEvent(stage="sequence_analysis", status=StageStatus.RUNNING, progress=0.0)
    yield PipelineEvent(stage="annotation", status=StageStatus.RUNNING, progress=0.0)

    async def _run_sequence_analysis() -> PipelineEvent:
        try:
            result = await sequence_analysis.run(record)
            return PipelineEvent(
                stage="sequence_analysis",
                status=StageStatus.COMPLETED,
                progress=1.0,
                data=result.model_dump(),
            )
        except Exception as e:
            return PipelineEvent(
                stage="sequence_analysis", status=StageStatus.FAILED,
                error=f"{type(e).__name__}: {e}",
            )

    async def _run_annotation() -> PipelineEvent:
        try:
            result = await annotation.run(record, http)
            return PipelineEvent(
                stage="annotation",
                status=StageStatus.COMPLETED,
                progress=1.0,
                data=result.model_dump(),
            )
        except Exception as e:
            return PipelineEvent(
                stage="annotation", status=StageStatus.FAILED,
                error=f"{type(e).__name__}: {e}",
            )

    tasks = [
        asyncio.create_task(_run_sequence_analysis()),
        asyncio.create_task(_run_annotation()),
    ]

    for coro in asyncio.as_completed(tasks):
        event = await coro
        yield event
