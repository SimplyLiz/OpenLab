"""openlab pipeline -- orchestrate multi-phase evidence collection and synthesis."""

import json

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from openlab.db import get_session_factory

_SessionLocal = get_session_factory()

app = typer.Typer(no_args_is_help=True)
console = Console()

# Phase definitions: ordered list of evidence sources per phase
PHASES = {
    1: {
        "name": "Homology & Basic Annotation",
        "sources": ["europepmc", "synwiki", "eggnog_online"],
        "description": "Literature search, SynWiki lookup, eggNOG functional annotation",
    },
    2: {
        "name": "Structure Prediction",
        "sources": ["esmfold", "alphafold", "foldseek"],
        "description": "ESMFold/AlphaFold structure prediction, Foldseek similarity",
    },
    3: {
        "name": "Context & Localization",
        "sources": ["operon_prediction", "genomic_neighborhood", "deeptmhmm", "signalp"],
        "description": "Operon prediction, genomic neighborhood, topology/signal peptide",
    },
    4: {
        "name": "Deep Homology",
        "sources": ["hhpred", "hhblits", "hmmscan", "prost"],
        "description": "HHpred, HHblits, hmmscan (Pfam), PROST remote homology",
    },
    5: {
        "name": "LLM Synthesis",
        "sources": [],  # Handled separately via synthesize
        "description": "LLM-based function prediction from collected evidence",
    },
}


@app.command(name="run")
def run_cmd(
    phase: int = typer.Option(None, "--phase", "-p", help="Run a single phase (1-5)"),
    phases: str = typer.Option(None, "--phases", help="Comma-separated phase numbers (e.g. 1,2,5)"),
    all_genes: bool = typer.Option(False, "--all-genes", help="Include known-function genes"),
):
    """Run pipeline phases to collect evidence and synthesize hypotheses."""
    from openlab.pipeline.evidence_runner import run_source

    if phase is not None:
        phase_list = [phase]
    elif phases:
        phase_list = [int(p.strip()) for p in phases.split(",")]
    else:
        phase_list = list(PHASES.keys())

    for p in phase_list:
        if p not in PHASES:
            console.print(f"[red]Unknown phase {p}. Valid: 1-5[/red]")
            raise typer.Exit(code=1)

    for p in phase_list:
        phase_info = PHASES[p]
        console.print(f"\n[bold cyan]Phase {p}: {phase_info['name']}[/bold cyan]")
        console.print(f"[dim]{phase_info['description']}[/dim]\n")

        if p == 5:
            # Synthesis phase
            from openlab.cli.synthesize import synthesize
            ctx = typer.Context(synthesize)
            synthesize(limit=50, dry_run=False)
            continue

        for source in phase_info["sources"]:
            try:
                with console.status(f"  Running {source}..."):
                    count = run_source(source, unknown_only=not all_genes)
                console.print(f"  [green]{source}: {count} evidence rows[/green]")
            except Exception as e:
                console.print(f"  [red]{source}: {e}[/red]")

    console.print("\n[bold green]Pipeline complete.[/bold green]")


@app.command(name="status")
def status_cmd():
    """Show evidence coverage per pipeline phase."""
    from openlab.pipeline.evidence_runner import evidence_status

    counts = evidence_status()

    table = Table(title="Pipeline Evidence Coverage")
    table.add_column("Phase", style="bold")
    table.add_column("Name")
    table.add_column("Sources")
    table.add_column("Evidence Count", justify="right")

    for p, info in PHASES.items():
        phase_count = sum(counts.get(s, 0) for s in info["sources"])
        source_str = ", ".join(info["sources"]) if info["sources"] else "(synthesis)"
        table.add_row(
            str(p),
            info["name"],
            source_str,
            str(phase_count),
        )

    console.print(table)

    total = sum(counts.values())
    console.print(f"\n[bold]Total evidence rows:[/bold] {total}")


@app.command(name="list")
def list_cmd():
    """Describe all pipeline phases."""
    for p, info in PHASES.items():
        console.print(Panel(
            f"[bold]{info['description']}[/bold]\n\n"
            f"Sources: {', '.join(info['sources']) or '(LLM synthesis)'}",
            title=f"Phase {p}: {info['name']}",
            border_style="cyan",
        ))
