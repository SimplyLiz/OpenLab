from pathlib import Path

from openlab.db.models.gene import Gene
from openlab.db.models.hypothesis import Hypothesis, HypothesisScope
from openlab.services import gene_service, import_service

FIXTURE = Path(__file__).parent.parent / "fixtures" / "mini_syn3a.gb"


def _seed(db):
    import_service.import_genbank(db, FIXTURE)


def test_list_genes(db):
    _seed(db)
    genes = gene_service.list_genes(db)
    assert len(genes) == 4


def test_list_genes_unknown_only(db):
    _seed(db)
    genes = gene_service.list_genes(db, unknown_only=True)
    # JCVISYN3A_0002 is hypothetical
    locus_tags = [g.locus_tag for g in genes]
    assert "JCVISYN3A_0002" in locus_tags
    assert "JCVISYN3A_0001" not in locus_tags


def test_get_gene_by_locus(db):
    _seed(db)
    gene = gene_service.get_gene_by_locus(db, "JCVISYN3A_0001")
    assert gene.name == "dnaA"


def test_search_genes(db):
    _seed(db)
    results = gene_service.search_genes(db, "dnaA")
    assert len(results) >= 1
    assert results[0].name == "dnaA"


def test_get_dossier(db):
    _seed(db)
    gene = gene_service.get_gene_by_locus(db, "JCVISYN3A_0001")
    dossier = gene_service.get_dossier(db, gene.gene_id)
    assert dossier["locus_tag"] == "JCVISYN3A_0001"
    assert dossier["evidence_count"] == 0


# ── extract_proposed_function tests ──────────────────────────────────


def test_extract_markdown_bold_predicted_function():
    """Extracts from '1. **Predicted function**: LOCUS likely ...' (real LLM format)."""
    hyp = Hypothesis(
        title="Predicted function for JCVISYN3A_0538",
        description=(
            "1. **Predicted function**: JCVISYN3A_0538 likely encodes a "
            "membrane-associated protein involved in ribosomal function.\n\n"
            "2. **Confidence score**: 0.7"
        ),
    )
    result = gene_service.extract_proposed_function(hyp)
    assert result == "Likely encodes a membrane-associated protein involved in ribosomal function."


def test_extract_markdown_bold_colon_inside():
    """Extracts from '1. **Predicted function:** LOCUS ...' (colon inside bold)."""
    hyp = Hypothesis(
        title="Predicted function for JCVISYN3A_0604",
        description=(
            "1. **Predicted function:** JCVISYN3A_0604 likely functions as a "
            "two-component sensor histidine kinase.\n\n"
            "2. **Confidence score:** 0.8"
        ),
    )
    result = gene_service.extract_proposed_function(hyp)
    assert result == "Likely functions as a two-component sensor histidine kinase."


def test_extract_plain_with_the_gene_prefix():
    """Strips 'The gene JCVISYN3A_XXXX' prefix from extracted text."""
    hyp = Hypothesis(
        title="Predicted function for JCVISYN3A_0623",
        description=(
            "1. Predicted function: The gene JCVISYN3A_0623 likely encodes a "
            "restriction-modification system S subunit.\n\n"
            "2. Confidence score: 0.7"
        ),
    )
    result = gene_service.extract_proposed_function(hyp)
    assert result == "Likely encodes a restriction-modification system S subunit."


def test_extract_plain_predicted_function():
    """Extracts 'Predicted function: ...' without markdown or locus tag."""
    hyp = Hypothesis(
        title="Predicted function for JCVISYN3A_0002",
        description=(
            "Based on evidence analysis:\n\n"
            "Predicted function: Membrane-associated protease with chaperone activity\n\n"
            "Confidence: 0.75"
        ),
    )
    result = gene_service.extract_proposed_function(hyp)
    assert result == "Membrane-associated protease with chaperone activity"


def test_extract_most_likely_function_pattern():
    """Extracts 'Most likely function: ...' variant."""
    hyp = Hypothesis(
        title="Predicted function for JCVISYN3A_0003",
        description="Most likely function: tRNA modification enzyme\nOther details...",
    )
    result = gene_service.extract_proposed_function(hyp)
    assert result == "tRNA modification enzyme"


def test_extract_numbered_list_fallback():
    """Extracts function from '1. ...' numbered list without 'Predicted function' label."""
    hyp = Hypothesis(
        title="Predicted function for JCVISYN3A_0004",
        description="Top candidates:\n1. ABC transporter permease subunit\n2. Membrane protein",
    )
    result = gene_service.extract_proposed_function(hyp)
    assert result == "ABC transporter permease subunit"


def test_extract_fallback_first_line_strips_bold():
    """Falls back to first line, stripping markdown and locus tag."""
    hyp = Hypothesis(
        title="Predicted function for JCVISYN3A_0604",
        description="** JCVISYN3A_0604 likely functions as a membrane protease",
    )
    result = gene_service.extract_proposed_function(hyp)
    assert result == "Likely functions as a membrane protease"


def test_extract_empty_description_uses_title():
    """Falls back to title when description is empty."""
    hyp = Hypothesis(
        title="Predicted function for JCVISYN3A_0006",
        description="",
    )
    result = gene_service.extract_proposed_function(hyp)
    assert result == "Predicted function for JCVISYN3A_0006"


def test_extract_none_description_uses_title():
    """Falls back to title when description is None."""
    hyp = Hypothesis(
        title="Predicted function for JCVISYN3A_0007",
        description=None,
    )
    result = gene_service.extract_proposed_function(hyp)
    assert result == "Predicted function for JCVISYN3A_0007"


def test_graduation_candidates_include_proposed_function(db):
    """list_graduation_candidates returns proposed_function from hypothesis description."""
    _seed(db)
    gene = gene_service.get_gene_by_locus(db, "JCVISYN3A_0002")  # hypothetical protein

    hyp = Hypothesis(
        title="Predicted function for JCVISYN3A_0002",
        description="Predicted function: Membrane protease\nConfidence: 0.8",
        scope=HypothesisScope.GENE,
        confidence_score=0.8,
        gene_id=gene.gene_id,
    )
    db.add(hyp)
    db.flush()

    candidates = gene_service.list_graduation_candidates(db, min_confidence=0.7)
    assert len(candidates) >= 1
    match = [c for c in candidates if c["locus_tag"] == "JCVISYN3A_0002"]
    assert len(match) == 1
    assert match[0]["proposed_function"] == "Membrane protease"
