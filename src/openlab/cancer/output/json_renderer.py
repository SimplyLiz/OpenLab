"""JSON report renderer for variant interpretation results."""

from __future__ import annotations

from typing import Any

from openlab.cancer.models.variant import VariantReport

_DISCLAIMER = (
    "FOR RESEARCH USE ONLY. This is not a validated clinical"
    " diagnostic tool. Do not use for clinical decision-making."
)


def render_json(report: VariantReport) -> dict[str, Any]:
    """Render a variant report as a JSON-serializable dict.

    Always includes the disclaimer field.
    """
    data: dict[str, Any] = dict(report.model_dump(mode="json"))
    # Ensure disclaimer is always present regardless of model state
    data["disclaimer"] = _DISCLAIMER
    return data
