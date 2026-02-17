"""Stage: Validation — compare simulation results against known biology."""

from __future__ import annotations

import logging
import math
from collections.abc import AsyncGenerator

from openlab.models import (
    CellSpec, PipelineEvent, SimulationSnapshot, StageStatus,
    ValidationCheck, ValidationResult,
)

logger = logging.getLogger(__name__)

STAGE = "validation"


async def run(
    cellspec: CellSpec,
    time_series: list[dict],
    summary: dict,
) -> AsyncGenerator[PipelineEvent, None]:
    """Validate simulation results against known JCVI-syn3.0 biology."""
    yield PipelineEvent(
        stage=STAGE, status=StageStatus.RUNNING, progress=0.0,
        data={"message": "Validating simulation results..."},
    )

    checks: list[ValidationCheck] = []

    # 1. Doubling time check (~2 hours for JCVI-syn3.0 in rich media,
    #    6-18 hours for M. genitalium)
    doubling_time_h = summary.get("doubling_time_hours")
    dt_passed = doubling_time_h is not None and 0.5 <= doubling_time_h <= 24.0
    checks.append(ValidationCheck(
        name="Doubling time",
        passed=dt_passed,
        expected="0.5–24 hours",
        actual=f"{doubling_time_h:.2f} hours" if doubling_time_h else "N/A",
        score=1.0 if dt_passed else 0.0,
    ))

    # 2. Positive growth rate
    final_gr = summary.get("final_growth_rate", 0)
    gr_passed = final_gr is not None and final_gr > 0
    checks.append(ValidationCheck(
        name="Positive growth rate",
        passed=gr_passed,
        expected="> 0",
        actual=f"{final_gr:.6f}" if final_gr else "0",
        score=1.0 if gr_passed else 0.0,
    ))

    # 3. Division count (expect ~10 divisions in 20hr simulation)
    total_divs = summary.get("total_divisions", 0)
    div_passed = total_divs >= 1
    checks.append(ValidationCheck(
        name="Cell division occurred",
        passed=div_passed,
        expected=">= 1 division",
        actual=f"{total_divs} divisions",
        score=min(1.0, total_divs / 10) if total_divs > 0 else 0.0,
    ))

    # 4. No metabolite depletion (check final ATP, glucose)
    snapshots = [SimulationSnapshot.model_validate(s) for s in time_series[-5:]] if time_series else []
    if snapshots:
        final = snapshots[-1]
        met_ok = final.atp > 0.01 and final.glucose > 0.01
    else:
        met_ok = False
    checks.append(ValidationCheck(
        name="Metabolite homeostasis",
        passed=met_ok,
        expected="ATP > 0.01 mM, glucose > 0.01 mM",
        actual=f"ATP={final.atp:.3f}, glucose={final.glucose:.3f}" if snapshots else "N/A",
        score=1.0 if met_ok else 0.0,
    ))

    # 5. Dry mass increase
    if len(time_series) >= 2:
        first = SimulationSnapshot.model_validate(time_series[0])
        mass_ratio = final.dry_mass / first.dry_mass if first.dry_mass > 0 else 0
        mass_ok = mass_ratio > 1.0
    else:
        mass_ratio = 0
        mass_ok = False
    checks.append(ValidationCheck(
        name="Mass accumulation",
        passed=mass_ok,
        expected="Final mass > initial mass",
        actual=f"Ratio: {mass_ratio:.2f}x" if mass_ratio > 0 else "N/A",
        score=min(1.0, mass_ratio / 2.0) if mass_ratio > 0 else 0.0,
    ))

    # Overall score
    scores = [c.score for c in checks]
    overall = sum(scores) / len(scores) if scores else 0.0

    result = ValidationResult(
        checks=checks,
        overall_score=round(overall, 3),
        mcc=None,  # MCC requires experimental data
        doubling_time_hours=doubling_time_h,
    )

    logger.info(f"Validation: {sum(1 for c in checks if c.passed)}/{len(checks)} checks passed, score={overall:.2f}")

    yield PipelineEvent(
        stage=STAGE,
        status=StageStatus.COMPLETED,
        progress=1.0,
        data=result.model_dump(),
    )
