"""Shared fixtures for cancer evidence source tests."""

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "cancer_responses"


@pytest.fixture
def clinvar_response():
    return json.loads((FIXTURES_DIR / "clinvar_tp53.json").read_text())


@pytest.fixture
def cosmic_response():
    return json.loads((FIXTURES_DIR / "cosmic_braf.json").read_text())


@pytest.fixture
def oncokb_response():
    return json.loads((FIXTURES_DIR / "oncokb_braf.json").read_text())


@pytest.fixture
def civic_response():
    return json.loads((FIXTURES_DIR / "civic_tp53.json").read_text())


@pytest.fixture
def cbioportal_response():
    return json.loads((FIXTURES_DIR / "cbioportal_tp53.json").read_text())


@pytest.fixture
def gdc_response():
    return json.loads((FIXTURES_DIR / "gdc_tp53.json").read_text())
