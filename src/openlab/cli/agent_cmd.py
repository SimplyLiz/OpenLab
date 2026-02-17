"""openlab agent — agent pipeline management commands."""

import asyncio

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command("run")
def run_agent(
    gene_symbol: str = typer.Argument(..., help="Gene symbol (e.g., TP53)"),
    cancer: str = typer.Option(None, "--cancer", "-c", help="Cancer type"),
):
    """Run a dossier agent for a gene."""
    asyncio.run(_run(gene_symbol, cancer))


async def _run(gene_symbol: str, cancer_type: str | None) -> None:
    from openlab.agents.scheduler import AgentScheduler

    scheduler = AgentScheduler()
    console.print(f"[bold]Running agent for [cyan]{gene_symbol}[/cyan]...[/bold]")
    record = await scheduler.run_once(gene_symbol, cancer_type)
    console.print(f"Status: [{'green' if record.status.value == 'completed' else 'red'}]{record.status.value}[/]")
    console.print(f"Run ID: {record.run_id}")
    console.print(f"Tool calls: {record.total_tool_calls}")
    if record.error:
        console.print(f"[red]Error: {record.error}[/red]")


@app.command("status")
def status(run_id: str = typer.Argument(..., help="Agent run ID")):
    """Check status of an agent run."""
    from openlab.agents.scheduler import AgentScheduler

    scheduler = AgentScheduler()
    record = scheduler.get_status(run_id)
    if not record:
        console.print(f"[red]Run {run_id} not found[/red]")
        raise typer.Exit(1)
    console.print(f"Run ID: {record.run_id}")
    console.print(f"Gene: {record.gene_symbol}")
    console.print(f"Status: {record.status.value}")


@app.command("history")
def history(limit: int = typer.Option(20, "--limit", "-n", help="Max results")):
    """List recent agent runs."""
    from openlab.agents.scheduler import AgentScheduler

    scheduler = AgentScheduler()
    runs = scheduler.list_runs(limit=limit)
    if not runs:
        console.print("[dim]No agent runs found.[/dim]")
        return

    table = Table(title="Agent Runs")
    table.add_column("Run ID")
    table.add_column("Gene")
    table.add_column("Cancer Type")
    table.add_column("Status")
    table.add_column("Tool Calls")

    for r in runs:
        table.add_row(
            r.run_id,
            r.gene_symbol,
            r.cancer_type or "-",
            r.status.value,
            str(r.total_tool_calls),
        )

    console.print(table)
