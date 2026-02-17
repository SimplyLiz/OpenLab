"""openlab export -- export data and import validation results."""

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from openlab.db import get_session_factory
from openlab.db.models.evidence import Evidence, EvidenceType
from openlab.services import export_service, gene_service

app = typer.Typer(no_args_is_help=True)
console = Console()

_SessionLocal = get_session_factory()


@app.command(name="dnaview")
def export_dnaview(
    output: Path = typer.Option(
        Path("data/export/dnaview_graduated.json"),
        "--output", "-o",
        help="Output JSON file path",
    ),
):
    """Export graduated genes for simulation.

    Produces a JSON file with all graduated genes, their predicted functions,
    confidence/convergence scores, and evidence summaries.
    """
    db = _SessionLocal()
    try:
        data = export_service.export_graduated_genes(db)

        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w") as f:
            json.dump(data, f, indent=2, default=str)

        console.print(
            f"[green]Exported {data['totalGraduated']} graduated genes "
            f"to {output}[/green]"
        )

        # Summary by category
        categories: dict[str, int] = {}
        for gene in data["genes"]:
            cat = gene["functionCategory"]
            categories[cat] = categories.get(cat, 0) + 1

        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            console.print(f"  {cat}: {count}")

    finally:
        db.close()


@app.command(name="import-validation")
def import_validation(
    path: Path = typer.Argument(
        ...,
        help="Path to KO validation evidence JSON",
    ),
):
    """Import function KO validation results as SIMULATION evidence.

    Reads a ko_validation_evidence.json and creates SIMULATION evidence
    records for each validated gene.
    """
    if not path.exists():
        console.print(f"[red]File not found: {path}[/red]")
        raise typer.Exit(code=1)

    with open(path) as f:
        entries = json.load(f)

    if not isinstance(entries, list):
        console.print("[red]Expected a JSON array of evidence entries[/red]")
        raise typer.Exit(code=1)

    db = _SessionLocal()
    try:
        imported = 0
        skipped = 0
        errors = 0

        for entry in entries:
            locus_tag = entry.get("locus_tag")
            if not locus_tag:
                errors += 1
                continue

            try:
                gene = gene_service.get_gene_by_locus(db, locus_tag)
            except Exception:
                console.print(f"  [yellow]Gene {locus_tag} not found, skipping[/yellow]")
                skipped += 1
                continue

            # Check for existing SIMULATION evidence
            existing = (
                db.query(Evidence)
                .filter(
                    Evidence.gene_id == gene.gene_id,
                    Evidence.evidence_type == EvidenceType.SIMULATION,
                )
                .first()
            )
            if existing:
                existing.payload = entry.get("payload", {})
                existing.confidence = entry.get("confidence", 0.5)
                existing.source_ref = entry.get("source_ref", "BioLab KO validation")
                console.print(f"  [blue]Updated {locus_tag}[/blue]")
            else:
                ev = Evidence(
                    gene_id=gene.gene_id,
                    evidence_type=EvidenceType.SIMULATION,
                    payload=entry.get("payload", {}),
                    confidence=entry.get("confidence", 0.5),
                    source_ref=entry.get("source_ref", "BioLab KO validation"),
                )
                db.add(ev)

            imported += 1

        db.commit()

        console.print(
            f"\n[green]Imported {imported} SIMULATION evidence records[/green]"
        )
        if skipped:
            console.print(f"[yellow]Skipped {skipped} (gene not found)[/yellow]")
        if errors:
            console.print(f"[red]Errors: {errors}[/red]")

        if imported > 0:
            table = Table(title="Validation Summary")
            table.add_column("Locus Tag")
            table.add_column("Score", justify="right")
            table.add_column("Interpretation")

            for entry in entries[:10]:
                payload = entry.get("payload", {})
                table.add_row(
                    entry.get("locus_tag", "?"),
                    f"{payload.get('validation_score', 0):.2f}",
                    payload.get("interpretation", "")[:60],
                )

            if len(entries) > 10:
                table.add_row("...", "...", f"({len(entries) - 10} more)")

            console.print(table)

    finally:
        db.close()
