"""openlab validate -- validation subcommands wrapping validation_service."""

import json

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from openlab.db import get_session_factory

_SessionLocal = get_session_factory()

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command(name="all")
def validate_all_cmd(
    bootstrap: bool = typer.Option(False, "--bootstrap", help="Include bootstrap stability"),
    bootstrap_limit: int = typer.Option(20, help="Max genes for bootstrap"),
    output_json: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Run all validation methods and produce a combined report."""
    from openlab.services import validation_service

    db = _SessionLocal()
    try:
        with console.status("Running validation..."):
            report = validation_service.validate_all(
                db, run_bootstrap=bootstrap, bootstrap_limit=bootstrap_limit,
            )

        if output_json:
            typer.echo(json.dumps(report, indent=2, default=str))
            return

        s = report["summary"]
        console.print(Panel(
            f"[bold]Ortholog accuracy:[/bold] {s['ortholog_accuracy']:.1%}\n"
            f"[bold]Consistency rate:[/bold]  {s['consistency_rate']:.1%}\n"
            f"[bold]Estimated FPR:[/bold]     {s['estimated_fpr']:.1%}",
            title="Validation Summary",
            border_style="cyan",
        ))
    finally:
        db.close()


@app.command(name="loo")
def loo_cmd(
    output_json: bool = typer.Option(False, "--json"),
):
    """Run leave-one-out validation on curated genes."""
    from openlab.services import validation_service

    db = _SessionLocal()
    try:
        with console.status("Running leave-one-out validation..."):
            results = validation_service.leave_one_out(db)

        if output_json:
            typer.echo(json.dumps(results, indent=2, default=str))
            return

        if not results:
            console.print("[yellow]No curated reclassifications found.[/yellow]")
            return

        table = Table(title=f"LOO Validation ({len(results)} genes)")
        table.add_column("Locus Tag", style="cyan")
        table.add_column("Match", justify="right")
        table.add_column("Pass")
        for r in results:
            table.add_row(
                r["locus_tag"],
                f"{r['match_score']:.2f}",
                "[green]PASS[/green]" if r["passed"] else "[red]FAIL[/red]",
            )
        console.print(table)
    finally:
        db.close()


@app.command(name="ortholog")
def ortholog_cmd(
    output_json: bool = typer.Option(False, "--json"),
):
    """Validate graduated genes against known M. genitalium orthologs."""
    from openlab.services import validation_service

    db = _SessionLocal()
    try:
        with console.status("Running ortholog validation..."):
            results = validation_service.ortholog_validation(db)

        if output_json:
            typer.echo(json.dumps(results, indent=2, default=str))
            return

        if not results:
            console.print("[yellow]No ortholog data available.[/yellow]")
            return

        passed = sum(1 for r in results if r["passed"])
        table = Table(title=f"Ortholog Validation ({passed}/{len(results)} passed)")
        table.add_column("Locus Tag", style="cyan")
        table.add_column("Proposed")
        table.add_column("Ortholog")
        table.add_column("Score", justify="right")
        table.add_column("Pass")

        for r in results:
            table.add_row(
                r["locus_tag"],
                (r["proposed_function"] or "")[:30],
                (r["ortholog_function"] or "")[:30],
                f"{r['combined_score']:.2f}",
                "[green]PASS[/green]" if r["passed"] else "[red]FAIL[/red]",
            )
        console.print(table)
    finally:
        db.close()


@app.command(name="consistency")
def consistency_cmd(
    output_json: bool = typer.Option(False, "--json"),
):
    """Check if graduated gene functions are consistent with evidence majority."""
    from openlab.services import validation_service

    db = _SessionLocal()
    try:
        with console.status("Running consistency check..."):
            results = validation_service.consistency_validation(db)

        if output_json:
            typer.echo(json.dumps(results, indent=2, default=str))
            return

        if not results:
            console.print("[yellow]No graduated genes to check.[/yellow]")
            return

        consistent = sum(1 for r in results if r["consistent"])
        table = Table(title=f"Consistency Check ({consistent}/{len(results)} consistent)")
        table.add_column("Locus Tag", style="cyan")
        table.add_column("Proposed Categories")
        table.add_column("Evidence Majority")
        table.add_column("Status")

        for r in results:
            table.add_row(
                r["locus_tag"],
                ", ".join(r["proposed_categories"][:3]) or "-",
                ", ".join(r["evidence_majority_categories"][:3]),
                "[green]OK[/green]" if r["consistent"] else "[red]INCONSISTENT[/red]",
            )
        console.print(table)
    finally:
        db.close()


@app.command(name="tiers")
def tiers_cmd(
    output_json: bool = typer.Option(False, "--json"),
):
    """Show confidence tier breakdown for graduated genes."""
    from openlab.services import validation_service

    db = _SessionLocal()
    try:
        with console.status("Building tiers..."):
            report = validation_service.build_confidence_tiers(db)

        if output_json:
            typer.echo(json.dumps(report, indent=2, default=str))
            return

        summary = report["summary"]
        breakdown = summary["tier_breakdown"]

        console.print(Panel(
            f"[bold]Total graduated:[/bold] {summary['total_graduated']}\n"
            f"[green]Tier 1 (High):[/green]     {breakdown.get('1', {}).get('count', 0)}\n"
            f"[yellow]Tier 2 (Moderate):[/yellow] {breakdown.get('2', {}).get('count', 0)}\n"
            f"Tier 3 (Low):      {breakdown.get('3', {}).get('count', 0)}\n"
            f"[red]Tier 4 (Flagged):[/red]  {breakdown.get('4', {}).get('count', 0)}",
            title="Confidence Tiers",
            border_style="cyan",
        ))
    finally:
        db.close()
