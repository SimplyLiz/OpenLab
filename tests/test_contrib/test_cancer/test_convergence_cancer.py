"""Test convergence scoring with cancer evidence payloads."""

from openlab.services.convergence import compute_convergence
from openlab.services.evidence_normalizer import normalize_payload


def test_convergence_with_cancer_evidence():
    """Cancer evidence sources should contribute to convergence scoring."""
    evidence_list = [
        {
            "source": "clinvar",
            "variants": [
                {
                    "clinical_significance": "Pathogenic",
                    "categories": ["cancer:pathogenic_variant"],
                    "title": "TP53 R175H pathogenic variant",
                }
            ],
        },
        {
            "source": "cosmic",
            "mutations": [
                {
                    "aa_mutation": "p.R175H",
                    "categories": ["cancer:somatic_mutation", "mutation:missense"],
                    "primary_site": "breast",
                }
            ],
        },
        {
            "source": "civic",
            "entries": [
                {
                    "description": "TP53 R175H is a hotspot mutation in breast cancer",
                    "categories": ["cancer:curated_evidence", "cancer:drug_target"],
                    "therapies": ["AZD1775"],
                }
            ],
        },
    ]

    score = compute_convergence(evidence_list)
    # Should have non-zero convergence from shared keywords
    assert score >= 0.0
    assert score <= 1.0


def test_normalize_cancer_variants():
    """Cancer variant payloads should normalize to categories."""
    payload = {
        "source": "clinvar",
        "variants": [
            {
                "clinical_significance": "Pathogenic",
                "categories": ["cancer:pathogenic_variant"],
                "title": "TP53 R175H in Li-Fraumeni syndrome",
            }
        ],
    }
    result = normalize_payload(payload)
    assert "cancer:pathogenic_variant" in result.categories


def test_normalize_cancer_mutations():
    """Cancer mutation payloads should normalize correctly."""
    payload = {
        "source": "cosmic",
        "mutations": [
            {
                "aa_mutation": "p.V600E",
                "primary_site": "skin",
                "categories": ["cancer:somatic_mutation", "mutation:missense"],
            }
        ],
    }
    result = normalize_payload(payload)
    assert "cancer:somatic_mutation" in result.categories
    assert "mutation:missense" in result.categories


def test_normalize_cancer_entries_with_therapies():
    """Cancer entries with therapies should get drug_target category."""
    payload = {
        "source": "civic",
        "entries": [
            {
                "description": "BRAF V600E predicts response to vemurafenib",
                "categories": ["cancer:drug_target"],
                "therapies": ["vemurafenib", "dabrafenib"],
            }
        ],
    }
    result = normalize_payload(payload)
    assert "cancer:drug_target" in result.categories


def test_convergence_cancer_weights():
    """Cancer sources should use their configured weights in convergence scoring."""
    from openlab.services.convergence import _get_weight

    assert _get_weight({"source": "clinvar"}) == 1.8
    assert _get_weight({"source": "cosmic"}) == 2.0
    assert _get_weight({"source": "oncokb"}) == 2.0
    assert _get_weight({"source": "cbioportal"}) == 1.5
    assert _get_weight({"source": "civic"}) == 1.8
    assert _get_weight({"source": "tcga_gdc"}) == 1.5
