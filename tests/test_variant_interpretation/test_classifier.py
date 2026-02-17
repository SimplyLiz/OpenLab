"""Tests for variant classifier."""

from openlab.cancer.classification.classifier import classify_all, classify_variant
from openlab.cancer.models.variant import (
    AnnotatedVariant,
    ClinicalSignificance,
    EvidenceItem,
    VariantRecord,
)


def _make_variant(gene: str = "TP53") -> VariantRecord:
    return VariantRecord(chrom="chr17", pos=7674220, ref="C", alt="T", gene_symbol=gene)


def test_classify_pathogenic():
    """High-confidence pathogenic evidence yields PATHOGENIC."""
    av = AnnotatedVariant(
        variant=_make_variant(),
        evidence=[
            EvidenceItem(
                source="clinvar",
                classification=ClinicalSignificance.PATHOGENIC,
                confidence=0.95,
            ),
            EvidenceItem(
                source="oncokb",
                classification=ClinicalSignificance.PATHOGENIC,
                confidence=0.8,
            ),
        ],
    )
    result = classify_variant(av)
    assert result.consensus_classification == ClinicalSignificance.PATHOGENIC
    assert result.confidence > 0.5


def test_classify_benign():
    """High-confidence benign evidence yields BENIGN."""
    av = AnnotatedVariant(
        variant=_make_variant(),
        evidence=[
            EvidenceItem(
                source="clinvar",
                classification=ClinicalSignificance.BENIGN,
                confidence=0.95,
            ),
        ],
    )
    result = classify_variant(av)
    assert result.consensus_classification == ClinicalSignificance.BENIGN


def test_classify_vus_no_evidence():
    """No evidence yields VUS with zero confidence."""
    av = AnnotatedVariant(variant=_make_variant())
    result = classify_variant(av)
    assert result.consensus_classification == ClinicalSignificance.VUS
    assert result.confidence == 0.0


def test_classify_disagreement():
    """Disagreeing sources tend toward VUS."""
    av = AnnotatedVariant(
        variant=_make_variant(),
        evidence=[
            EvidenceItem(
                source="clinvar",
                classification=ClinicalSignificance.PATHOGENIC,
                confidence=0.5,
            ),
            EvidenceItem(
                source="civic",
                classification=ClinicalSignificance.BENIGN,
                confidence=0.5,
            ),
        ],
    )
    result = classify_variant(av)
    # With disagreement, should be VUS or intermediate
    assert result.consensus_classification in (
        ClinicalSignificance.VUS,
        ClinicalSignificance.LIKELY_PATHOGENIC,
        ClinicalSignificance.LIKELY_BENIGN,
    )


def test_classify_actionable_from_therapies():
    """Variants with therapies are marked actionable."""
    av = AnnotatedVariant(
        variant=_make_variant("BRAF"),
        evidence=[
            EvidenceItem(
                source="oncokb",
                classification=ClinicalSignificance.PATHOGENIC,
                confidence=0.8,
                therapies=["vemurafenib"],
            ),
        ],
    )
    result = classify_variant(av)
    assert result.is_actionable is True


def test_classify_actionable_from_pathogenic():
    """Pathogenic variants are actionable even without therapies."""
    av = AnnotatedVariant(
        variant=_make_variant(),
        evidence=[
            EvidenceItem(
                source="clinvar",
                classification=ClinicalSignificance.PATHOGENIC,
                confidence=0.95,
            ),
        ],
    )
    result = classify_variant(av)
    assert result.is_actionable is True


def test_classify_all():
    """classify_all processes list of variants."""
    variants = [
        AnnotatedVariant(
            variant=_make_variant(),
            evidence=[EvidenceItem(
                source="clinvar",
                classification=ClinicalSignificance.PATHOGENIC,
                confidence=0.9,
            )],
        ),
        AnnotatedVariant(variant=_make_variant("BRAF")),
    ]
    results = classify_all(variants)
    assert len(results) == 2
    assert results[0].consensus_classification == ClinicalSignificance.PATHOGENIC
    assert results[1].consensus_classification == ClinicalSignificance.VUS
