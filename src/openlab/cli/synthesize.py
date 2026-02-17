"""openlab synthesize -- standalone LLM synthesis for gene function prediction."""

import json

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from openlab.db import get_session_factory

_SessionLocal = get_session_factory()

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.callback(invoke_without_command=True)
def synthesize(
    locus_tag: str = typer.Option(None, "--locus-tag", "-t", help="Specific gene locus tag"),
    limit: int = typer.Option(10, "--limit", "-n", help="Max genes to synthesize"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show prompts without calling LLM"),
):
    """Run LLM synthesis on genes with evidence but no hypothesis."""
    from openlab.db.models.evidence import Evidence
    from openlab.db.models.gene import Gene
    from openlab.services import gene_service, hypothesis_service, llm_service
    from openlab.services.convergence import compute_convergence
    from openlab.services.llm_synthesis import build_evidence_prompt

    db = _SessionLocal()
    try:
        if locus_tag:
            gene = gene_service.get_gene_by_locus(db, locus_tag)
            genes = [gene]
        else:
            all_genes = gene_service.list_genes(db, unknown_only=True, limit=500)
            genes = []
            for g in all_genes:
                existing = hypothesis_service.get_hypothesis_for_gene(db, g.gene_id)
                if not existing:
                    genes.append(g)
                if len(genes) >= limit:
                    break

        if not genes:
            console.print("[yellow]No genes need synthesis.[/yellow]")
            return

        console.print(f"[cyan]Synthesizing {len(genes)} genes...[/cyan]\n")

        results = Table(title="Synthesis Results")
        results.add_column("Locus Tag", style="cyan")
        results.add_column("Evidence", justify="right")
        results.add_column("Confidence", justify="right")
        results.add_column("Status")

        for gene in genes:
            evidence_rows = (
                db.query(Evidence)
                .filter(Evidence.gene_id == gene.gene_id)
                .order_by(Evidence.evidence_type)
                .all()
            )
            if not evidence_rows:
                results.add_row(gene.locus_tag, "0", "-", "[yellow]no evidence[/yellow]")
                continue

            evidence_list = [
                {"source": (ev.payload or {}).get("source", ev.source_ref or ""), **(ev.payload or {})}
                for ev in evidence_rows
            ]
            conv_score = compute_convergence(evidence_list)

            prompt = build_evidence_prompt(
                locus_tag=gene.locus_tag,
                product=gene.product or "hypothetical protein",
                protein_length=gene.length or 0,
                evidence_list=evidence_list,
                convergence_score=conv_score,
            )

            if dry_run:
                console.print(Panel(prompt[:1000], title=f"Prompt: {gene.locus_tag}", border_style="blue"))
                results.add_row(gene.locus_tag, str(len(evidence_rows)), "-", "[blue]dry run[/blue]")
                continue

            try:
                response = llm_service.synthesize(
                    prompt, purpose="synthesis", gene_locus_tag=gene.locus_tag,
                )

                confidence = _extract_confidence(response)
                evidence_ids = [ev.evidence_id for ev in evidence_rows]

                hypothesis_service.create_hypothesis(
                    db=db,
                    title=f"Predicted function for {gene.locus_tag}",
                    description=response,
                    confidence_score=confidence,
                    evidence_ids=evidence_ids,
                    gene_id=gene.gene_id,
                )

                results.add_row(
                    gene.locus_tag,
                    str(len(evidence_rows)),
                    f"{confidence:.2f}",
                    "[green]saved[/green]",
                )
            except Exception as e:
                results.add_row(gene.locus_tag, str(len(evidence_rows)), "-", f"[red]{e}[/red]")

        console.print(results)

    finally:
        db.close()


def _extract_confidence(text: str) -> float:
    """Extract confidence score from LLM response."""
    import re
    for pattern in [r"[Cc]onfidence[:\s]+(\d+\.?\d*)", r"(\d+\.?\d*)\s*/\s*1\.0"]:
        m = re.search(pattern, text)
        if m:
            val = float(m.group(1))
            return max(0.0, min(1.0, val / 100.0 if val > 1.0 else val))
    return 0.5
