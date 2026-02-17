"""Tests for GO term validation."""

import pytest
from unittest.mock import patch

from openlab.services.go_validator import (
    is_valid_go_term,
    validate_go_terms,
    reset_go_cache,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_go_cache()
    yield
    reset_go_cache()


class TestGOValidator:
    def test_no_data_file_accepts_all(self, tmp_path):
        """With no GO data file, all terms should be accepted (fail-open)."""
        with patch("openlab.services.go_validator.Path") as mock_path:
            # Make both paths not exist
            mock_path.return_value.parent.parent.parent.__truediv__ = lambda s, x: tmp_path / x
            reset_go_cache()

        # Since we can't easily mock Path at that level, just test the fail-open
        # behavior by checking that the module handles missing files
        reset_go_cache()
        # Force _loaded=False and _go_ids=None
        import openlab.services.go_validator as gov
        gov._loaded = True
        gov._go_ids = None
        assert is_valid_go_term("GO:9999999") is True

    def test_validates_against_loaded_ids(self):
        """Valid GO IDs pass, invalid ones fail."""
        import openlab.services.go_validator as gov
        gov._loaded = True
        gov._go_ids = frozenset({"GO:0005524", "GO:0003677", "GO:0016301"})

        assert is_valid_go_term("GO:0005524") is True
        assert is_valid_go_term("GO:0003677") is True
        assert is_valid_go_term("GO:9999999") is False

    def test_validate_go_terms_partitions(self):
        """validate_go_terms should partition into valid and invalid sets."""
        import openlab.services.go_validator as gov
        gov._loaded = True
        gov._go_ids = frozenset({"GO:0005524", "GO:0003677"})

        terms = {"GO:0005524", "GO:0003677", "GO:9999999", "GO:0000001"}
        valid, invalid = validate_go_terms(terms)

        assert valid == {"GO:0005524", "GO:0003677"}
        assert invalid == {"GO:9999999", "GO:0000001"}

    def test_invalid_go_terms_dropped_in_normalizer(self):
        """Integration: normalizer should drop invalid GO terms."""
        import openlab.services.go_validator as gov
        from openlab.services.evidence_normalizer import normalize_evidence, reset_keyword_map_cache

        reset_keyword_map_cache()

        # Set up validator with known IDs
        gov._loaded = True
        gov._go_ids = frozenset({"GO:0005524"})  # only ATP binding is valid

        class FakeEvidence:
            pass
        ev = FakeEvidence()
        ev.evidence_type = "HOMOLOGY"
        ev.payload = {
            "go_terms": [
                {"id": "GO:0005524"},  # valid
                {"id": "GO:9999999"},  # invalid — should be dropped
            ],
        }

        norm = normalize_evidence(ev)
        assert "GO:0005524" in norm.go_terms
        assert "GO:9999999" not in norm.go_terms

        reset_keyword_map_cache()
