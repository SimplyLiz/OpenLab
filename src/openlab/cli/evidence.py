"""openlab evidence -- manage evidence sources and batch collection."""

import json

import typer
from rich.console import Console
from rich.table import Table

from openlab.db import get_session_factory

_SessionLocal = get_session_factory()

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command(name="run")
def run_cmd(
    source: str = typer.Argument(..., help="Evidence source name (e.g. esmfold, synwiki)"),
    all_genes: bool = typer.Option(False, "--all-genes", help="Run on all genes, not just unknown"),
):
    """Run a single evidence source against DB genes."""
    from openlab.pipeline.evidence_runner import run_source

    try:
        with console.status(f"Running {source}..."):
            count = run_source(source, unknown_only=not all_genes)
        console.print(f"[green]{source}: {count} evidence rows stored[/green]")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command(name="run-all")
def run_all_cmd(
    all_genes: bool = typer.Option(False, "--all-genes", help="Run on all genes"),
):
    """Run all available evidence sources."""
    from openlab.pipeline.evidence_runner import run_all_sources

    console.print("[cyan]Running all evidence sources...[/cyan]\n")
    results = run_all_sources(unknown_only=not all_genes)

    table = Table(title="Evidence Collection Results")
    table.add_column("Source", style="cyan")
    table.add_column("Count", justify="right")
    table.add_column("Status")

    total = 0
    for source, count in sorted(results.items()):
        if count < 0:
            table.add_row(source, "-", "[red]error[/red]")
        elif count == 0:
            table.add_row(source, "0", "[yellow]no results[/yellow]")
        else:
            table.add_row(source, str(count), "[green]ok[/green]")
            total += count

    console.print(table)
    console.print(f"\n[bold]Total new evidence:[/bold] {total}")


@app.command(name="status")
def status_cmd(
    output_json: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Show evidence counts per source in the database."""
    from openlab.pipeline.evidence_runner import evidence_status

    counts = evidence_status()

    if output_json:
        typer.echo(json.dumps(counts, indent=2))
        return

    if not counts:
        console.print("[yellow]No evidence in database.[/yellow]")
        return

    table = Table(title="Evidence by Source")
    table.add_column("Source", style="cyan")
    table.add_column("Count", justify="right")

    total = 0
    for source, count in sorted(counts.items(), key=lambda x: -x[1]):
        table.add_row(source, str(count))
        total += count

    console.print(table)
    console.print(f"\n[bold]Total:[/bold] {total}")


@app.command(name="list-sources")
def list_sources_cmd():
    """List available evidence sources and their status."""
    from openlab.pipeline.evidence_runner import list_sources

    sources = list_sources()

    table = Table(title="Evidence Sources")
    table.add_column("Source", style="cyan")
    table.add_column("Module")
    table.add_column("Status")

    for s in sources:
        status_style = "[green]available[/green]" if s["status"] == "available" else "[yellow]missing_deps[/yellow]"
        table.add_row(s["name"], s["module"], status_style)

    console.print(table)
