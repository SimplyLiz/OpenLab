"""CLI for paper-to-pipeline conversion.

Usage:
    openlab paper-to-pipeline methods.pdf --output pipeline.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(help="Paper-to-pipeline extraction")


@app.command("extract")
def extract(
    pdf_path: str = typer.Argument(help="Path to PDF file"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output YAML file path"),
    max_pages: int = typer.Option(50, "--max-pages", help="Maximum pages to process"),
    validate: bool = typer.Option(True, "--validate/--no-validate", help="Validate output"),
) -> None:
    """Extract methods from a paper and generate a pipeline config."""
    from rich.console import Console

    console = Console()

    path = Path(pdf_path)
    if not path.exists():
        console.print(f"[red]Error: File not found: {pdf_path}[/red]")
        raise typer.Exit(1)

    # Step 1: Extract text
    console.print(f"[bold]Extracting text from:[/bold] {pdf_path}")
    from openlab.paper.extractor import extract_text
    try:
        text = extract_text(pdf_path, max_pages=max_pages)
    except Exception as e:
        console.print(f"[red]Extraction failed: {e}[/red]")
        raise typer.Exit(1)
    console.print(f"  Extracted {len(text)} characters")

    # Step 2: Find methods section
    console.print("[bold]Finding Methods section...[/bold]")
    from openlab.paper.methods_finder import find_methods_section
    methods = find_methods_section(text)
    if not methods:
        console.print("[yellow]Warning: Could not identify Methods section. Using full text.[/yellow]")
        methods = text
    else:
        console.print(f"  Found Methods section ({len(methods)} chars)")

    # Step 3: Parse protocol
    console.print("[bold]Parsing protocol...[/bold]")
    from openlab.paper.methods_parser import parse_methods
    protocol = parse_methods(methods, paper_title=path.stem)
    console.print(f"  Found {len(protocol.steps)} steps, {len(protocol.techniques_mentioned)} techniques")

    # Step 4: Map to pipeline
    console.print("[bold]Mapping to pipeline...[/bold]")
    from openlab.paper.pipeline_mapper import map_protocol_to_pipeline
    pipeline = map_protocol_to_pipeline(protocol)
    console.print(f"  Generated {len(pipeline.stages)} pipeline stages")

    if pipeline.warnings:
        for warning in pipeline.warnings:
            console.print(f"  [yellow]Warning: {warning}[/yellow]")

    # Step 5: Generate YAML
    from openlab.paper.yaml_generator import generate_yaml
    yaml_content = generate_yaml(pipeline)

    # Step 6: Validate
    if validate:
        from openlab.paper.validator import validate_yaml
        errors = validate_yaml(yaml_content)
        if errors:
            console.print("[red]Validation errors:[/red]")
            for error in errors:
                console.print(f"  [red]- {error}[/red]")
        else:
            console.print("[green]Validation passed[/green]")

    # Output
    if output:
        Path(output).write_text(yaml_content)
        console.print(f"[green]Pipeline written to {output}[/green]")
    else:
        console.print("\n" + yaml_content)
