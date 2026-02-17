"""Tests for CLI analyze commands."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from openlab.cli.main import app

runner = CliRunner()


@patch("openlab.cli.analyze._SessionLocal")
@patch("openlab.cli.analyze.gene_service")
@patch("openlab.cli.analyze.hypothesis_service")
def test_dossier_json(mock_hyp_svc, mock_gene_svc, mock_session_cls):
    mock_db = MagicMock()
    mock_session_cls.return_value = mock_db

    mock_gene = MagicMock()
    mock_gene.gene_id = 1
    mock_gene_svc.get_gene_by_locus.return_value = mock_gene
    mock_gene_svc.get_dossier.return_value = {
        "gene_id": 1,
        "locus_tag": "JCVISYN3A_0005",
        "name": None,
        "product": "hypothetical protein",
        "essentiality": "essential",
        "evidence_count": 3,
        "evidence_by_type": {"HOMOLOGY": [{"payload": {"source": "BLAST"}, "confidence": 0.8, "source_ref": None, "evidence_id": 1, "quality_score": None}]},
        "features": [],
    }

    result = runner.invoke(app, ["analyze", "dossier", "JCVISYN3A_0005", "--json"])
    assert result.exit_code == 0
    assert "JCVISYN3A_0005" in result.output


@patch("openlab.cli.analyze._SessionLocal")
@patch("openlab.cli.analyze.gene_service")
@patch("openlab.cli.analyze.hypothesis_service")
def test_dossier_rich_output(mock_hyp_svc, mock_gene_svc, mock_session_cls):
    mock_db = MagicMock()
    mock_session_cls.return_value = mock_db

    mock_gene = MagicMock()
    mock_gene.gene_id = 1
    mock_gene_svc.get_gene_by_locus.return_value = mock_gene
    mock_gene_svc.get_dossier.return_value = {
        "gene_id": 1,
        "locus_tag": "JCVISYN3A_0005",
        "name": None,
        "product": None,
        "essentiality": None,
        "evidence_count": 0,
        "evidence_by_type": {},
        "features": [],
    }
    mock_hyp_svc.get_hypothesis_for_gene.return_value = None

    result = runner.invoke(app, ["analyze", "dossier", "JCVISYN3A_0005"])
    assert result.exit_code == 0


@patch("openlab.cli.analyze._SessionLocal")
@patch("openlab.cli.analyze.gene_service")
def test_deep_prompt_only(mock_gene_svc, mock_session_cls):
    mock_db = MagicMock()
    mock_session_cls.return_value = mock_db

    mock_gene = MagicMock()
    mock_gene.gene_id = 1
    mock_gene.locus_tag = "JCVISYN3A_0005"
    mock_gene.length = 300
    mock_gene.strand = 1
    mock_gene.start = 4000
    mock_gene.end = 4300
    mock_gene.product = None
    mock_gene_svc.get_gene_by_locus.return_value = mock_gene

    mock_ev = MagicMock()
    mock_ev.evidence_type = MagicMock()
    mock_ev.evidence_type.value = "HOMOLOGY"
    mock_ev.evidence_id = 1
    mock_ev.payload = {"source": "BLAST", "hits": [{"accession": "P12345"}]}
    mock_ev.confidence = 0.8

    # Evidence is imported inside deep_cmd, so mock via the models module
    with patch("openlab.db.models.evidence.Evidence") as MockEvidence:
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_ev]

        result = runner.invoke(app, ["analyze", "deep", "JCVISYN3A_0005", "--prompt-only"])
        assert result.exit_code == 0
        assert "JCVISYN3A_0005" in result.output


@patch("openlab.cli.analyze._SessionLocal")
@patch("openlab.cli.analyze.gene_service")
def test_deep_no_evidence(mock_gene_svc, mock_session_cls):
    mock_db = MagicMock()
    mock_session_cls.return_value = mock_db

    mock_gene = MagicMock()
    mock_gene.gene_id = 1
    mock_gene_svc.get_gene_by_locus.return_value = mock_gene

    with patch("openlab.db.models.evidence.Evidence"):
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        result = runner.invoke(app, ["analyze", "deep", "JCVISYN3A_0005"])
        assert result.exit_code == 1
        assert "No evidence" in result.output


def test_analyze_help():
    result = runner.invoke(app, ["analyze", "--help"])
    assert result.exit_code == 0
    assert "dossier" in result.output
    assert "deep" in result.output
    assert "batch" in result.output
    assert "status" in result.output
