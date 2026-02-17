"""Tests for transposon mutagenesis TSV parser."""

from pathlib import Path

import pytest

from openlab.exceptions import ParseError
from openlab.ingestion.transposon import parse_transposon_tsv

FIXTURE = Path(__file__).parent.parent / "fixtures" / "mini_transposon.tsv"


def test_parse_fixture():
    entries = parse_transposon_tsv(FIXTURE)
    assert len(entries) == 4


def test_first_entry_fields():
    entries = parse_transposon_tsv(FIXTURE)
    e = entries[0]
    assert e.locus_tag == "JCVISYN3A_0001"
    assert e.essentiality == "essential"
    assert e.tn5_class == "e"
    assert e.n_insertions == 0
    assert e.notes == "DnaA replication initiation"


def test_all_classes_present():
    entries = parse_transposon_tsv(FIXTURE)
    classes = {e.tn5_class for e in entries}
    assert classes == {"e", "i", "n", "d"}


def test_file_not_found():
    with pytest.raises(ParseError, match="File not found"):
        parse_transposon_tsv("/nonexistent/file.tsv")


def test_bad_class(tmp_path):
    bad = tmp_path / "bad.tsv"
    bad.write_text(
        "locus_tag\tessentiality\ttn5_class\tn_insertions\tnotes\n"
        "GENE_001\tessential\tx\t0\t\n"
    )
    with pytest.raises(ParseError, match="invalid tn5_class"):
        parse_transposon_tsv(bad)


def test_bad_insertions(tmp_path):
    bad = tmp_path / "bad.tsv"
    bad.write_text(
        "locus_tag\tessentiality\ttn5_class\tn_insertions\tnotes\n"
        "GENE_001\tessential\te\tNaN\t\n"
    )
    with pytest.raises(ParseError, match="n_insertions must be an integer"):
        parse_transposon_tsv(bad)


def test_empty_file(tmp_path):
    empty = tmp_path / "empty.tsv"
    empty.write_text(
        "locus_tag\tessentiality\ttn5_class\tn_insertions\tnotes\n"
    )
    with pytest.raises(ParseError, match="No data rows"):
        parse_transposon_tsv(empty)


def test_missing_column(tmp_path):
    bad = tmp_path / "bad.tsv"
    bad.write_text("locus_tag\tessentiality\n" "GENE_001\tessential\n")
    with pytest.raises(ParseError, match="Missing required columns"):
        parse_transposon_tsv(bad)
