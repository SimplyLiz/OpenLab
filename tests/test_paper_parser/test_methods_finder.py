"""Tests for methods section finder."""

from openlab.paper.methods_finder import find_methods_section


def test_find_standard_heading(sample_methods_text):
    """Find methods section with standard heading."""
    methods = find_methods_section(sample_methods_text)
    assert methods
    assert "Cell Culture" in methods or "RNA Extraction" in methods
    assert "Introduction" not in methods.split("\n")[0]


def test_methods_excludes_results(sample_methods_text):
    """Methods section should not include Results."""
    methods = find_methods_section(sample_methods_text)
    assert "1,247 differentially expressed genes" not in methods


def test_find_alternative_heading():
    """Find methods with alternative heading style."""
    text = """# Experimental Procedures

Cells were cultured and incubated at 37°C for 24 hours.
RNA was extracted using TRIzol protocol.

# Results

We found significant differences."""
    methods = find_methods_section(text)
    assert "cultured" in methods
    assert "significant differences" not in methods


def test_no_methods_section():
    """Returns empty string when no methods found."""
    text = "This is just an abstract with no methods section at all."
    methods = find_methods_section(text)
    assert methods == ""


def test_methods_heading_variations():
    """Various heading styles should be detected."""
    headings = [
        "## Methods",
        "## Materials and Methods",
        "## METHODS",
        "## Experimental Procedures",
        "## Online Methods",
        "## STAR Methods",
    ]
    for heading in headings:
        text = f"""{heading}

We performed RNA-seq and analyzed the results.

## Results

We found things."""
        methods = find_methods_section(text)
        assert methods, f"Failed to find methods with heading: {heading}"
