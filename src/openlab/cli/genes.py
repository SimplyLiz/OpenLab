"""BioLab genes -- gene subcommands."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from openlab.config import settings
from openlab.db import get_session_factory
from openlab.db.models.hypothesis import Hypothesis
from openlab.services import gene_service, hypothesis_service, import_service

_SessionLocal = get_session_factory()

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command(name="import")
def import_cmd(
    path: Path = typer.Argument(..., help="Path to GenBank or FASTA file"),
):
    """Import genes from a GenBank or FASTA file."""
    db = _SessionLocal()
    try:
        suffix = path.suffix.lower()
        if suffix in (".gb", ".gbk", ".genbank"):
            result = import_service.import_genbank(db, path)
        elif suffix in (".fasta", ".fa", ".fna"):
            result = import_service.import_fasta(db, path)
        else:
            console.print(f"[red]Unknown file format: {suffix}[/red]")
            raise typer.Exit(code=1)

        console.print(f"[green]Import complete:[/green]")
        for key, value in result.items():
            console.print(f"  {key}: {value}")
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1)
    finally:
        db.close()


@app.command(name="list")
def list_cmd(
    unknown_only: bool = typer.Option(False, "--unknown-only", help="Show only unknown-function genes"),
    limit: int = typer.Option(500, help="Maximum genes to show"),
):
    """List genes in the database."""
    db = _SessionLocal()
    try:
        genes = gene_service.list_genes(db, unknown_only=unknown_only, limit=limit)

        if not genes:
            console.print("[yellow]No genes found.[/yellow]")
            return

        table = Table(title=f"Genes ({len(genes)} shown)")
        table.add_column("ID", style="dim")
        table.add_column("Locus Tag", style="cyan")
        table.add_column("Name")
        table.add_column("Product", max_width=50)
        table.add_column("Start", justify="right")
        table.add_column("End", justify="right")
        table.add_column("Strand")

        for g in genes:
            table.add_row(
                str(g.gene_id),
                g.locus_tag,
                g.name or "-",
                (g.product or "-")[:50],
                str(g.start),
                str(g.end),
                "+" if g.strand == 1 else "-",
            )

        console.print(table)
    finally:
        db.close()


@app.command(name="show")
def show_cmd(
    locus_tag: str = typer.Argument(..., help="Locus tag (e.g. JCVISYN3A_0001)"),
):
    """Show details for a single gene."""
    db = _SessionLocal()
    try:
        gene = gene_service.get_gene_by_locus(db, locus_tag)

        console.print(f"\n[bold cyan]{gene.locus_tag}[/bold cyan]")
        console.print(f"  Name:          {gene.name or '-'}")
        console.print(f"  Product:       {gene.product or '-'}")
        console.print(f"  Location:      {gene.start}..{gene.end} ({'+'  if gene.strand == 1 else '-'})")
        console.print(f"  Length:         {gene.length} bp")
        console.print(f"  Essentiality:  {gene.essentiality or '-'}")
        console.print(f"  Sequence:      {gene.sequence[:60]}{'...' if len(gene.sequence) > 60 else ''}")
        if gene.protein_sequence:
            console.print(f"  Protein:       {gene.protein_sequence[:60]}{'...' if len(gene.protein_sequence) > 60 else ''}")

        if gene.evidence:
            console.print(f"\n  [bold]Evidence ({len(gene.evidence)}):[/bold]")
            for ev in gene.evidence:
                console.print(f"    - {ev.evidence_type.value}: {ev.source_ref or '-'} (conf={ev.confidence})")

        if gene.features:
            console.print(f"\n  [bold]Features ({len(gene.features)}):[/bold]")
            for f in gene.features:
                console.print(f"    - {f.feature_type} {f.start}-{f.end} ({f.source})")

        # Show graduation status
        if gene.graduated_at:
            console.print(f"\n  [bold green]Graduated:[/bold green]  {gene.proposed_function}")
            console.print(f"  Graduated at:  {gene.graduated_at:%Y-%m-%d %H:%M}")
            if gene.graduation_hypothesis_id:
                console.print(f"  Hypothesis ID: {gene.graduation_hypothesis_id}")

        console.print()
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1)
    finally:
        db.close()


@app.command(name="graduate")
def graduate_cmd(
    locus_tag: str = typer.Argument(..., help="Locus tag to graduate"),
    proposed_function: Optional[str] = typer.Option(
        None, "--function", "-f", help="Proposed function (auto-detected from hypothesis if omitted)"
    ),
    hypothesis_id: Optional[int] = typer.Option(
        None, "--hypothesis-id", "-h", help="Hypothesis ID to link"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Graduate a gene -- assign a proposed function."""
    db = _SessionLocal()
    try:
        gene = gene_service.get_gene_by_locus(db, locus_tag)

        # Auto-detect hypothesis if not given
        if hypothesis_id is None and proposed_function is None:
            hyp = hypothesis_service.get_hypothesis_for_gene(db, gene.gene_id)
            if hyp:
                hypothesis_id = hyp.hypothesis_id
                proposed_function = gene_service.extract_proposed_function(hyp)
                console.print(
                    f"[dim]Auto-detected hypothesis #{hyp.hypothesis_id}: "
                    f"{proposed_function} (confidence={hyp.confidence_score:.2f})[/dim]"
                )
            else:
                console.print("[red]No hypothesis found. Provide --function explicitly.[/red]")
                raise typer.Exit(code=1)

        if proposed_function is None:
            console.print("[red]--function is required when --hypothesis-id is given without --function.[/red]")
            raise typer.Exit(code=1)

        if not yes:
            console.print(Panel(
                f"[bold]{locus_tag}[/bold]\n"
                f"Current product: {gene.product or '-'}\n"
                f"Proposed function: [green]{proposed_function}[/green]\n"
                f"Hypothesis ID: {hypothesis_id or 'none'}",
                title="Graduate Gene",
            ))
            typer.confirm("Proceed?", abort=True)

        result = gene_service.graduate_gene(
            db, gene.gene_id, proposed_function, hypothesis_id=hypothesis_id
        )
        console.print(f"[green]Graduated {result.locus_tag} → {result.proposed_function}[/green]")
    except (typer.Abort, SystemExit):
        raise
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1)
    finally:
        db.close()


@app.command(name="ungraduate")
def ungraduate_cmd(
    locus_tag: str = typer.Argument(..., help="Locus tag to un-graduate"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Reverse graduation -- return gene to unknown pool."""
    db = _SessionLocal()
    try:
        gene = gene_service.get_gene_by_locus(db, locus_tag)

        if not yes:
            console.print(Panel(
                f"[bold]{locus_tag}[/bold]\n"
                f"Current proposed function: {gene.proposed_function or '-'}\n"
                f"Graduated at: {gene.graduated_at}",
                title="Un-graduate Gene",
            ))
            typer.confirm("Reverse this graduation?", abort=True)

        gene_service.ungraduate_gene(db, gene.gene_id)
        console.print(f"[yellow]Un-graduated {locus_tag} — returned to unknown pool[/yellow]")
    except (typer.Abort, SystemExit):
        raise
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1)
    finally:
        db.close()


@app.command(name="graduate-batch")
def graduate_batch_cmd(
    threshold: float = typer.Option(
        settings.graduation_confidence_threshold,
        "--threshold", "-t",
        help="Minimum hypothesis confidence",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show candidates without graduating"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Graduate all without confirmation"),
    limit: int = typer.Option(100, help="Max candidates to show"),
):
    """Show graduation candidates and optionally graduate them."""
    db = _SessionLocal()
    try:
        candidates = gene_service.list_graduation_candidates(
            db, min_confidence=threshold, limit=limit
        )

        if not candidates:
            console.print(f"[yellow]No candidates above threshold {threshold}[/yellow]")
            return

        table = Table(title=f"Graduation Candidates (threshold={threshold})")
        table.add_column("Locus Tag", style="cyan")
        table.add_column("Product", max_width=40)
        table.add_column("Hyp ID", justify="right")
        table.add_column("Proposed Function", max_width=50)
        table.add_column("Confidence", justify="right")

        for c in candidates:
            table.add_row(
                c["locus_tag"],
                (c["product"] or "-")[:40],
                str(c["hypothesis_id"]),
                c["proposed_function"][:50],
                f"{c['confidence']:.2f}" if c["confidence"] else "-",
            )

        console.print(table)
        console.print(f"\n[bold]{len(candidates)}[/bold] candidates found.")

        if dry_run:
            console.print("[dim]Dry run — no changes made.[/dim]")
            return

        if not yes:
            typer.confirm(f"Graduate all {len(candidates)} genes?", abort=True)

        graduated = 0
        for c in candidates:
            gene_service.graduate_gene(
                db,
                c["gene_id"],
                c["proposed_function"],
                hypothesis_id=c["hypothesis_id"],
            )
            graduated += 1

        console.print(f"[green]Graduated {graduated} genes.[/green]")
    except (typer.Abort, SystemExit):
        raise
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1)
    finally:
        db.close()


@app.command(name="fix-functions")
def fix_functions_cmd(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show changes without applying"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Retroactively fix proposed_function for graduated genes.

    Re-extracts the actual predicted function from each gene's linked
    hypothesis description, replacing the incorrect hypothesis title.
    """
    db = _SessionLocal()
    try:
        graduated = gene_service.list_graduated_genes(db, limit=10000)

        if not graduated:
            console.print("[yellow]No graduated genes found.[/yellow]")
            return

        fixes = []
        for gene in graduated:
            if not gene.graduation_hypothesis_id:
                continue
            hyp = db.query(Hypothesis).filter(
                Hypothesis.hypothesis_id == gene.graduation_hypothesis_id
            ).first()
            if not hyp:
                continue

            new_function = gene_service.extract_proposed_function(hyp)
            if new_function != gene.proposed_function:
                fixes.append((gene, new_function, gene.proposed_function))

        if not fixes:
            console.print("[green]All graduated genes already have correct proposed_function.[/green]")
            return

        table = Table(title=f"Proposed Function Fixes ({len(fixes)})")
        table.add_column("Locus Tag", style="cyan")
        table.add_column("Old Function", max_width=40, style="red")
        table.add_column("New Function", max_width=40, style="green")

        for gene, new_fn, old_fn in fixes:
            table.add_row(
                gene.locus_tag,
                (old_fn or "-")[:40],
                new_fn[:40],
            )

        console.print(table)

        if dry_run:
            console.print(f"[dim]Dry run — {len(fixes)} genes would be updated.[/dim]")
            return

        if not yes:
            typer.confirm(f"Update proposed_function for {len(fixes)} genes?", abort=True)

        for gene, new_fn, _ in fixes:
            gene.proposed_function = new_fn

        db.commit()
        console.print(f"[green]Fixed proposed_function for {len(fixes)} genes.[/green]")
    except (typer.Abort, SystemExit):
        raise
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1)
    finally:
        db.close()


@app.command(name="graduated")
def graduated_cmd(
    limit: int = typer.Option(500, help="Maximum genes to show"),
):
    """List all graduated genes."""
    db = _SessionLocal()
    try:
        genes = gene_service.list_graduated_genes(db, limit=limit)

        if not genes:
            console.print("[yellow]No graduated genes yet.[/yellow]")
            return

        table = Table(title=f"Graduated Genes ({len(genes)})")
        table.add_column("Locus Tag", style="cyan")
        table.add_column("Proposed Function", max_width=60)
        table.add_column("Graduated At")
        table.add_column("Hyp ID", justify="right", style="dim")

        for g in genes:
            table.add_row(
                g.locus_tag,
                (g.proposed_function or "-")[:60],
                g.graduated_at.strftime("%Y-%m-%d %H:%M") if g.graduated_at else "-",
                str(g.graduation_hypothesis_id or "-"),
            )

        console.print(table)
    finally:
        db.close()
