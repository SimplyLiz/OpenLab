"""Shared fixtures for paper parser tests."""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "papers"


@pytest.fixture
def sample_methods_text():
    return (FIXTURES_DIR / "sample_methods.txt").read_text()


@pytest.fixture
def methods_only_text():
    """Just the methods section without intro/results."""
    text = (FIXTURES_DIR / "sample_methods.txt").read_text()
    # Extract between Materials and Methods + Results
    from openlab.paper.methods_finder import find_methods_section
    return find_methods_section(text)
