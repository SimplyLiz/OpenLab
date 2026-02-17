"""CellForge CLI (PRD §7.3) — built with Typer."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

app = typer.Typer(
    name="cellforge",
    help="CellForge: Genome-agnostic whole-cell simulation engine.",
    add_completion=False,
)


@app.command()
def annotate(
    fasta: Path = typer.Argument(..., help="Path to genome FASTA file"),
    output: Path = typer.Option("annotation_output", "--output", "-o", help="Output directory"),
) -> None:
    """Run the genome annotation pipeline."""
    if not fasta.exists():
        typer.echo(f"Error: FASTA file not found: {fasta}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Annotating {fasta} → {output}")
    output.mkdir(parents=True, exist_ok=True)

    from openlab.cellforge.core.simulation import Simulation

    sim = Simulation.from_fasta(fasta)
    kb = sim.knowledge_base

    # Write KB summary
    summary_path = output / "knowledge_base.json"
    with open(summary_path, "w") as f:
        json.dump(kb.summary() if kb else {}, f, indent=2)

    typer.echo(f"Knowledge base summary written to {summary_path}")
    if kb:
        s = kb.summary()
        typer.echo(f"  Organism: {s['organism']}")
        typer.echo(f"  Genome length: {s['genome_length']:,} bp")
        typer.echo(f"  GC content: {s['gc_content']:.1%}")


@app.command()
def run(
    config: Path = typer.Argument(..., help="Path to simulation config JSON"),
    output: Path = typer.Option("output", "--output", "-o", help="Output directory"),
    seed: int = typer.Option(42, "--seed", "-s", help="Random seed"),
) -> None:
    """Run a whole-cell simulation."""
    if not config.exists():
        typer.echo(f"Error: Config file not found: {config}", err=True)
        raise typer.Exit(1)

    with open(config) as f:
        config_data = json.load(f)

    from openlab.cellforge.core.config import SimulationConfig
    from openlab.cellforge.core.simulation import Simulation

    sim_config = SimulationConfig(seed=seed, output_dir=str(output), **config_data)
    sim = Simulation(config=sim_config)

    typer.echo(f"Running simulation: {sim_config.organism_name}")
    typer.echo(f"  Total time: {sim_config.total_time}s, dt: {sim_config.dt}s")
    typer.echo(f"  Seed: {seed}")

    sim.initialize()
    final_state = sim.run()

    output.mkdir(parents=True, exist_ok=True)
    sim.save_checkpoint(output / "final_checkpoint.json")

    typer.echo(f"\nSimulation complete at t={final_state.get('time', 0):.1f}s")
    typer.echo(f"  Growth rate: {final_state.get('growth_rate', 0):.6f} /s")
    typer.echo(f"  Cell mass: {final_state.get('cell_mass', 0):.1f} fg")
    typer.echo(f"  Checkpoint saved to {output / 'final_checkpoint.json'}")


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Bind host"),
    port: int = typer.Option(8420, "--port", "-p", help="Bind port"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload"),
) -> None:
    """Start the CellForge API server."""
    try:
        import uvicorn
    except ImportError:
        typer.echo("Error: uvicorn not installed. Run: pip install uvicorn", err=True)
        raise typer.Exit(1)

    typer.echo(f"Starting CellForge server on {host}:{port}")
    uvicorn.run(
        "openlab.cellforge.api.app:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.command()
def info() -> None:
    """Show CellForge version and system info."""
    typer.echo("CellForge v0.1.0")

    try:
        from openlab.cellforge._engine import __version__ as engine_version
        typer.echo(f"  Engine: {engine_version} (native)")
    except ImportError:
        typer.echo("  Engine: Python-only (native extension not built)")

    typer.echo(f"  Python: {sys.version.split()[0]}")

    # Check optional dependencies
    for pkg, label in [
        ("cobra", "COBRApy (FBA)"),
        ("gillespy2", "GillesPy2 (SSA)"),
        ("redis", "Redis"),
    ]:
        try:
            __import__(pkg)
            typer.echo(f"  {label}: available")
        except ImportError:
            typer.echo(f"  {label}: not installed")


@app.command()
def references(
    download: bool = typer.Option(False, "--download", help="Download reference data"),
) -> None:
    """Manage reference genome data."""
    if download:
        typer.echo("Reference data download not yet implemented.")
        typer.echo("Provide a FASTA file directly to 'cellforge annotate' or 'cellforge run'.")
    else:
        typer.echo("Reference data management")
        typer.echo("  Use --download to fetch reference genomes")


@app.command()
def benchmark(
    organism: str = typer.Option("demo", "--organism", help="Organism to benchmark"),
    duration: float = typer.Option(100.0, "--duration", "-d", help="Simulation duration (s)"),
) -> None:
    """Run performance benchmarks."""
    import time

    from openlab.cellforge.core.config import SimulationConfig
    from openlab.cellforge.core.simulation import Simulation

    config = SimulationConfig(organism_name=organism, total_time=duration, dt=1.0)
    sim = Simulation(config=config)

    typer.echo(f"Benchmarking {organism} for {duration}s...")
    sim.initialize()

    t0 = time.perf_counter()
    sim.run()
    elapsed = time.perf_counter() - t0

    steps = int(duration / config.dt)
    typer.echo(f"\nResults:")
    typer.echo(f"  Wall time: {elapsed:.2f}s")
    typer.echo(f"  Sim steps: {steps}")
    typer.echo(f"  Steps/sec: {steps / elapsed:.0f}")
    typer.echo(f"  Speedup:   {duration / elapsed:.1f}x real-time")


if __name__ == "__main__":
    app()
