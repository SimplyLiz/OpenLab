"""CLI for variant interpretation.

Usage:
    openlab variants interpret sample.vcf --tumor-type breast --genome hg38
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(help="Variant interpretation and annotation")


@app.command("interpret")
def interpret(
    vcf_path: str = typer.Argument(help="Path to VCF file"),
    tumor_type: str = typer.Option("", "--tumor-type", "-t", help="Tumor type (e.g., breast, colorectal)"),
    genome: str = typer.Option("hg38", "--genome", "-g", help="Genome build (hg19, hg38)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    fmt: str = typer.Option("markdown", "--format", "-f", help="Output format: markdown or json"),
    concurrency: int = typer.Option(10, "--concurrency", help="Max concurrent API calls"),
) -> None:
    """Interpret variants from a VCF file."""
    from rich.console import Console

    console = Console()

    path = Path(vcf_path)
    if not path.exists():
        console.print(f"[red]Error: VCF file not found: {vcf_path}[/red]")
        raise typer.Exit(1)

    from openlab.cancer.models.variant import GenomeBuild

    try:
        build = GenomeBuild(genome)
    except ValueError:
        console.print(f"[red]Error: Invalid genome build: {genome}. Use hg19 or hg38.[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Parsing VCF:[/bold] {vcf_path}")

    from openlab.cancer.vcf.parser import parse_vcf
    variants, metadata = parse_vcf(vcf_path, build)
    console.print(f"  Parsed {len(variants)} variants")

    # Add HGVS notation
    from openlab.cancer.vcf.hgvs_converter import add_hgvs_to_variants
    variants = add_hgvs_to_variants(variants, build)

    # Annotate
    console.print("[bold]Annotating variants...[/bold]")

    import httpx
    from openlab.cancer.annotation.annotator import annotate_variants
    from openlab.cancer.classification.classifier import classify_all
    from openlab.cancer.models.variant import VariantReport

    async def _run_annotation():
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as http:
            annotated = await annotate_variants(variants, http, max_concurrency=concurrency)
            return classify_all(annotated)

    classified = asyncio.run(_run_annotation())

    # Build report
    pathogenic_count = sum(
        1 for v in classified
        if v.consensus_classification.value in ("pathogenic", "likely_pathogenic")
    )
    actionable_count = sum(1 for v in classified if v.is_actionable)

    report = VariantReport(
        sample_id=metadata.get("samples", [""])[0] if metadata.get("samples") else "",
        tumor_type=tumor_type,
        genome_build=build,
        variants=classified,
        total_variants_parsed=len(variants),
        total_annotated=sum(1 for v in classified if v.evidence),
        total_pathogenic=pathogenic_count,
        total_actionable=actionable_count,
        reproducibility={
            "vcf_hash": metadata.get("file_hash", ""),
            "genome_build": build.value,
            "concurrency": concurrency,
        },
    )

    # Render
    if fmt == "json":
        from openlab.cancer.output.json_renderer import render_json
        import json
        content = json.dumps(render_json(report), indent=2)
    else:
        from openlab.cancer.output.markdown_renderer import render_markdown
        content = render_markdown(report)

    if output:
        Path(output).write_text(content)
        console.print(f"[green]Report written to {output}[/green]")
    else:
        console.print(content)

    console.print(f"\n[bold]Summary:[/bold] {len(variants)} variants, "
                  f"{pathogenic_count} pathogenic/likely pathogenic, "
                  f"{actionable_count} actionable")
