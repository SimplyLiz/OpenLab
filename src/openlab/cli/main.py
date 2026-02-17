"""CLI entry point."""

import typer

from openlab.cli.genes import app as genes_app

app = typer.Typer(
    name="openlab",
    help="OpenLab — Open Bioinformatics Platform",
    no_args_is_help=True,
)

app.add_typer(genes_app, name="genes", help="Gene operations")


def _register_lazy():
    """Register subcommands that have heavier imports."""
    from openlab.cli.analyze import app as analyze_app
    from openlab.cli.export import app as export_app
    from openlab.cli.db import init_cmd
    from openlab.cli.evidence import app as evidence_app
    from openlab.cli.synthesize import app as synthesize_app
    from openlab.cli.pipeline_cmd import app as pipeline_app
    from openlab.cli.validate import app as validate_app

    app.add_typer(analyze_app, name="analyze", help="Deep gene analysis & LLM synthesis")
    app.add_typer(export_app, name="export", help="Export data for cross-project integration")
    app.add_typer(evidence_app, name="evidence", help="Evidence source management")
    app.add_typer(synthesize_app, name="synthesize", help="LLM function synthesis")
    app.add_typer(pipeline_app, name="pipeline", help="Multi-phase evidence pipeline")
    app.add_typer(validate_app, name="validate", help="Validation and quality checks")
    app.command(name="init")(init_cmd)

    from openlab.cellforge.cli.main import app as cellforge_app

    app.add_typer(cellforge_app, name="cellforge", help="CellForge whole-cell simulation engine")

    from openlab.cli.dossier import app as dossier_app
    from openlab.cli.agent_cmd import app as agent_app

    app.add_typer(dossier_app, name="dossier", help="Gene dossier generation")
    app.add_typer(agent_app, name="agent", help="Agent pipeline management")

    from openlab.cli.variants import app as variants_app
    from openlab.cli.paper import app as paper_app

    app.add_typer(variants_app, name="variants", help="Variant interpretation and annotation")
    app.add_typer(paper_app, name="paper-to-pipeline", help="Extract pipeline from paper methods")


_register_lazy()


if __name__ == "__main__":
    app()
