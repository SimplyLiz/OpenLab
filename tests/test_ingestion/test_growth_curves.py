"""Tests for growth curve CSV parser."""

from pathlib import Path

import pytest

from openlab.exceptions import ParseError
from openlab.ingestion.growth_curves import parse_growth_curves

FIXTURE = Path(__file__).parent.parent / "fixtures" / "mini_growth.csv"


def test_parse_fixture():
    result = parse_growth_curves(FIXTURE)
    # 3 groups: ko/rep1, wt/rep1, wt/rep2
    assert len(result.entries) == 3


def test_strains():
    result = parse_growth_curves(FIXTURE)
    assert result.strains == ["JCVISYN3A_0001_ko", "wild_type"]


def test_max_time():
    result = parse_growth_curves(FIXTURE)
    assert result.max_time == 6.0


def test_timepoints_and_values():
    result = parse_growth_curves(FIXTURE)
    ko = [e for e in result.entries if e.strain == "JCVISYN3A_0001_ko"][0]
    assert ko.timepoints == [0, 2, 4, 6]
    assert ko.od_values == [0.05, 0.08, 0.15, 0.22]
    assert ko.replicate == 1


def test_replicates():
    result = parse_growth_curves(FIXTURE)
    wt_entries = [e for e in result.entries if e.strain == "wild_type"]
    assert len(wt_entries) == 2
    reps = {e.replicate for e in wt_entries}
    assert reps == {1, 2}


def test_file_not_found():
    with pytest.raises(ParseError, match="File not found"):
        parse_growth_curves("/nonexistent/file.csv")


def test_missing_column(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("strain,time_h\nWT,0\n")
    with pytest.raises(ParseError, match="Missing required columns"):
        parse_growth_curves(bad)


def test_empty_file(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("strain,time_h,od600\n")
    with pytest.raises(ParseError, match="No data rows"):
        parse_growth_curves(empty)


def test_bad_time(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("strain,time_h,od600\nWT,abc,0.1\n")
    with pytest.raises(ParseError, match="time_h must be numeric"):
        parse_growth_curves(bad)


def test_bad_od(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("strain,time_h,od600\nWT,0,bad\n")
    with pytest.raises(ParseError, match="od600 must be numeric"):
        parse_growth_curves(bad)


def test_no_replicate_column(tmp_path):
    """When replicate column is absent, default to 1."""
    f = tmp_path / "norep.csv"
    f.write_text("strain,time_h,od600\nWT,0,0.1\nWT,2,0.3\n")
    result = parse_growth_curves(f)
    assert len(result.entries) == 1
    assert result.entries[0].replicate == 1
    assert len(result.entries[0].timepoints) == 2
