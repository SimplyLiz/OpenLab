"""Tests for claim extraction and synthesis."""

from openlab.agents.synthesizer import extract_claims


def test_extract_pmid_citations():
    text = (
        "TP53 mutations are found in over 50% of human cancers [PMID:20301340]. "
        "The protein acts as a tumor suppressor by inducing apoptosis [PMID:17482078] (0.95)."
    )
    claims = extract_claims(text)
    assert len(claims) >= 1
    # At least one claim should have PMID citations
    cited = [c for c in claims if c.citations]
    assert len(cited) >= 1
    assert any("PMID:20301340" in c.citations for c in cited)


def test_extract_doi_citations():
    text = "BRAF V600E is the most common mutation in melanoma [DOI:10.1038/nature09454] (0.9)."
    claims = extract_claims(text)
    assert len(claims) >= 1
    doi_claims = [c for c in claims if any("DOI:" in c for c in c.citations)]
    assert len(doi_claims) >= 1


def test_speculation_marker():
    text = "[SPECULATIVE] TP53 may interact with a novel signaling pathway (0.2)."
    claims = extract_claims(text)
    assert len(claims) >= 1
    assert claims[0].is_speculative


def test_no_citations_means_speculative():
    text = "The gene probably has important regulatory functions in cell cycle control."
    claims = extract_claims(text)
    for claim in claims:
        assert claim.is_speculative
        assert claim.confidence == 0.0


def test_confidence_extraction():
    text = "TP53 R175H is a hotspot mutation in colorectal cancer [PMID:12345678] (0.85)."
    claims = extract_claims(text)
    confident = [c for c in claims if c.confidence > 0]
    assert len(confident) >= 1
    assert confident[0].confidence == 0.85


def test_mixed_citations():
    text = (
        "Multiple studies confirm TP53's role [PMID:12345] [DOI:10.1234/test] (0.9). "
        "[SPECULATIVE] Novel p53 interaction with MDM4 requires further study (0.3)."
    )
    claims = extract_claims(text)
    assert len(claims) >= 2
    # First claim should have both citation types
    first = claims[0]
    assert len(first.citations) >= 1
    # Second should be speculative
    speculative = [c for c in claims if c.is_speculative]
    assert len(speculative) >= 1


def test_empty_input():
    claims = extract_claims("")
    assert claims == []


def test_short_sentences_skipped():
    text = "Yes. No. Maybe."
    claims = extract_claims(text)
    assert claims == []
