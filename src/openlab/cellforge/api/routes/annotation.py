"""Annotation API routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from openlab.cellforge.api.schemas import AnnotationRequest, AnnotationStatusResponse

router = APIRouter(prefix="/annotation", tags=["annotation"])

# In-memory annotation job store
_annotation_jobs: dict[str, dict] = {}


@router.post("/", response_model=AnnotationStatusResponse)
async def start_annotation(request: AnnotationRequest) -> AnnotationStatusResponse:
    """Start a genome annotation job."""
    job_id = str(uuid.uuid4())[:8]

    _annotation_jobs[job_id] = {
        "status": "queued",
        "stage": "initializing",
        "progress": 0.0,
        "genome_fasta": request.genome_fasta,
        "output_dir": request.output_dir,
    }

    return AnnotationStatusResponse(
        job_id=job_id,
        status="queued",
        stage="initializing",
        progress=0.0,
    )


@router.get("/{job_id}", response_model=AnnotationStatusResponse)
async def get_annotation_status(job_id: str) -> AnnotationStatusResponse:
    """Get annotation job status."""
    if job_id not in _annotation_jobs:
        raise HTTPException(status_code=404, detail=f"Annotation job {job_id} not found")

    job = _annotation_jobs[job_id]
    return AnnotationStatusResponse(
        job_id=job_id,
        status=job["status"],
        stage=job.get("stage", ""),
        progress=job.get("progress", 0.0),
    )
