"""Growth curve CSV parser — OD600 vs time data."""

import csv
from dataclasses import dataclass, field
from pathlib import Path

from openlab.exceptions import ParseError


@dataclass
class GrowthCurveData:
    strain: str
    timepoints: list[float] = field(default_factory=list)
    od_values: list[float] = field(default_factory=list)
    replicate: int = 1


@dataclass
class GrowthCurveResult:
    entries: list[GrowthCurveData]
    strains: list[str]
    max_time: float


def parse_growth_curves(path: Path | str) -> GrowthCurveResult:
    """Parse growth curve CSV data.

    Expected columns: strain, time_h, od600, replicate (optional)
    """
    path = Path(path)
    if not path.exists():
        raise ParseError(f"File not found: {path}")

    groups: dict[tuple[str, int], GrowthCurveData] = {}
    max_time = 0.0

    with open(path, newline="") as fh:
        reader = csv.DictReader(fh)

        if reader.fieldnames is None:
            raise ParseError("Empty CSV file")

        required = {"strain", "time_h", "od600"}
        missing = required - set(reader.fieldnames)
        if missing:
            raise ParseError(f"Missing required columns: {missing}")

        for lineno, row in enumerate(reader, start=2):
            strain = row["strain"].strip()
            if not strain:
                raise ParseError(f"Line {lineno}: empty strain")

            try:
                time_h = float(row["time_h"].strip())
            except ValueError:
                raise ParseError(
                    f"Line {lineno}: time_h must be numeric, got '{row['time_h']}'"
                )

            try:
                od600 = float(row["od600"].strip())
            except ValueError:
                raise ParseError(
                    f"Line {lineno}: od600 must be numeric, got '{row['od600']}'"
                )

            replicate = 1
            if "replicate" in row and row["replicate"].strip():
                try:
                    replicate = int(row["replicate"].strip())
                except ValueError:
                    raise ParseError(
                        f"Line {lineno}: replicate must be integer, "
                        f"got '{row['replicate']}'"
                    )

            key = (strain, replicate)
            if key not in groups:
                groups[key] = GrowthCurveData(
                    strain=strain, replicate=replicate
                )

            groups[key].timepoints.append(time_h)
            groups[key].od_values.append(od600)

            if time_h > max_time:
                max_time = time_h

    if not groups:
        raise ParseError("No data rows in CSV file")

    entries = list(groups.values())
    strains = sorted({e.strain for e in entries})

    return GrowthCurveResult(
        entries=entries,
        strains=strains,
        max_time=max_time,
    )
