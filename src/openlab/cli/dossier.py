"""openlab dossier — generate gene research dossiers."""

import asyncio
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command("generate")
@app.callback(invoke_without_command=True)
def generate(
    gene_symbol: str = typer.Argument(..., help="Gene symbol (e.g., TP53, BRAF)"),
    cancer: str = typer.Option(None, "--cancer", "-c", help="Cancer type (e.g., colorectal, breast)"),
    output: Path = typer.Option(None, "--output", "-o", help="Output file path"),
    format: str = typer.Option("markdown", "--format", "-f", help="Output format: markdown or json"),
    no_critic: bool = typer.Option(False, "--no-critic", help="Skip critic validation"),
):
    """Generate a gene dossier with cited cancer research."""
    asyncio.run(_run_dossier(gene_symbol, cancer, output, format, no_critic))


async def _run_dossier(
    gene_symbol: str,
    cancer_type: str | None,
    output: Path | None,
    fmt: str,
    no_critic: bool,
) -> None:
    from openlab.agents.agent_models import AgentEventType, GeneDossier
    from openlab.agents.runner import run_dossier_agent
    from openlab.agents.reporter import render_markdown, render_json

    console.print(f"\n[bold]Generating dossier for [cyan]{gene_symbol}[/cyan]", end="")
    if cancer_type:
        console.print(f" ([yellow]{cancer_type}[/yellow] cancer)", end="")
    console.print("[/bold]\n")

    dossier_data: dict = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Starting agent...", total=None)

        async for event in run_dossier_agent(gene_symbol, cancer_type):
            if event.event_type == AgentEventType.PLAN_CREATED:
                progress.update(task, description="Plan created, fetching gene identity...")
            elif event.event_type == AgentEventType.TOOL_STARTED:
                stage = event.stage
                progress.update(task, description=f"Running {stage}...")
            elif event.event_type == AgentEventType.TOOL_COMPLETED:
                progress.update(task, description=f"Completed {event.stage}")
            elif event.event_type == AgentEventType.SYNTHESIS_STARTED:
                progress.update(task, description="LLM synthesis in progress...")
            elif event.event_type == AgentEventType.SYNTHESIS_COMPLETED:
                progress.update(task, description="Synthesis complete, validating...")
            elif event.event_type == AgentEventType.CRITIC_STARTED:
                progress.update(task, description="Running critic validation...")
            elif event.event_type == AgentEventType.CRITIC_COMPLETED:
                valid = event.data.get("citations_valid", 0)
                invalid = event.data.get("citations_invalid", 0)
                progress.update(
                    task,
                    description=f"Critic done: {valid} valid, {invalid} invalid citations",
                )
            elif event.event_type == AgentEventType.DOSSIER_COMPLETED:
                dossier_data = event.data
                progress.update(task, description="Dossier complete!")
            elif event.event_type == AgentEventType.RUN_FAILED:
                console.print(f"\n[red]Error: {event.error}[/red]")
                raise typer.Exit(1)

    if not dossier_data:
        console.print("[red]No dossier data produced.[/red]")
        raise typer.Exit(1)

    # Summary
    console.print(Panel(
        f"[green]Dossier complete[/green]\n"
        f"Gene: {dossier_data.get('gene_symbol', gene_symbol)}\n"
        f"Sections: {dossier_data.get('sections', 0)}\n"
        f"Claims: {dossier_data.get('claims', 0)}\n"
        f"Convergence: {dossier_data.get('convergence_score', 0):.3f}\n"
        f"Tool calls: {dossier_data.get('total_tool_calls', 0)}",
        title="Summary",
    ))

    # For actual output rendering, we'd need the full dossier object
    # The streaming approach gives us events, not the final object
    # In production, the runner would also persist the dossier
    if output:
        console.print(f"\n[dim]Output would be written to {output}[/dim]")
