"""openlab analyze -- deep gene analysis CLI commands."""

import json
import sys

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from openlab.db import get_session_factory
from openlab.db.models.gene import Gene
from openlab.services import gene_service, hypothesis_service

_SessionLocal = get_session_factory()

app = typer.Typer(no_args_is_help=True)
console = Console()


def _build_prompt(gene: Gene, evidence_rows: list) -> str:
    """Build LLM prompt from gene + evidence for function prediction."""
    lines = [
        f"You are a molecular biologist analyzing gene {gene.locus_tag}.",
        f"Gene product: {gene.product or 'Unknown'}",
        f"Length: {gene.length} bp, Strand: {'+' if gene.strand == 1 else '-'}",
        f"Essentiality: {gene.essentiality or 'unknown'}",
        "",
        f"Below are {len(evidence_rows)} evidence records. Synthesize them to predict "
        "this gene's molecular function.",
        "",
    ]
    for ev in evidence_rows:
        payload_str = json.dumps(ev.payload, default=str)[:500]
        conf_str = f" (confidence={ev.confidence:.2f})" if ev.confidence else ""
        lines.append(f"[{ev.evidence_type.value}]{conf_str}: {payload_str}")

    lines.extend([
        "",
        "Provide:",
        "1. Predicted molecular function (1-2 sentences)",
        "2. Confidence level (0.0-1.0)",
        "3. Key evidence supporting this prediction",
        "4. Any conflicting evidence or caveats",
    ])
    return "\n".join(lines)


def _extract_confidence(text: str) -> float:
    """Extract confidence score from LLM response text."""
    import re
    patterns = [
        r"[Cc]onfidence[:\s]+(\d+\.?\d*)",
        r"(\d+\.?\d*)\s*/\s*1\.0",
        r"(\d+\.?\d*)\s+confidence",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            val = float(m.group(1))
            if val > 1.0:
                val = val / 100.0
            return max(0.0, min(1.0, val))
    return 0.5


@app.command(name="dossier")
def dossier_cmd(
    locus_tag: str = typer.Argument(..., help="Locus tag (e.g. JCVISYN3A_0005)"),
    output_json: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Print a full evidence dossier for a gene."""
    db = _SessionLocal()
    try:
        gene = gene_service.get_gene_by_locus(db, locus_tag)
        dossier = gene_service.get_dossier(db, gene.gene_id)

        if output_json:
            typer.echo(json.dumps(dossier, indent=2, default=str))
            return

        console.print()
        console.print(Panel(
            f"[bold]{dossier['locus_tag']}[/bold]  "
            f"{dossier['product'] or 'Uncharacterized protein'}\n"
            f"Essentiality: {dossier['essentiality'] or 'unknown'}  |  "
            f"Evidence records: {dossier['evidence_count']}",
            title="Gene Dossier",
            border_style="cyan",
        ))

        for etype, records in dossier["evidence_by_type"].items():
            console.print(f"\n[bold yellow]{etype}[/bold yellow] ({len(records)} records)")
            for rec in records:
                payload = rec["payload"] or {}
                source = payload.get("source", "?")
                conf = rec["confidence"]
                conf_str = f"conf={conf:.2f}" if conf is not None else ""
                details = _format_evidence(etype, payload)
                console.print(f"  [{source}] {details} {conf_str}")

        if dossier["features"]:
            console.print(f"\n[bold yellow]PROTEIN FEATURES[/bold yellow] ({len(dossier['features'])})")
            for feat in dossier["features"]:
                console.print(
                    f"  {feat['feature_type']} {feat['start']}-{feat['end']} ({feat['source']})"
                )

        hyp = hypothesis_service.get_hypothesis_for_gene(db, gene.gene_id)
        if hyp:
            console.print(f"\n[bold green]HYPOTHESIS[/bold green]")
            console.print(f"  Title:       {hyp.title}")
            console.print(f"  Status:      {hyp.status.value}")
            console.print(f"  Confidence:  {hyp.confidence_score:.2f}" if hyp.confidence_score else "  Confidence: -")
            if hyp.description:
                console.print(f"\n  [dim]{hyp.description[:500]}{'...' if len(hyp.description) > 500 else ''}[/dim]")

        console.print()

    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1)
    finally:
        db.close()


@app.command(name="deep")
def deep_cmd(
    locus_tag: str = typer.Argument(..., help="Locus tag to analyze"),
    prompt_only: bool = typer.Option(False, "--prompt-only", help="Print prompt without calling LLM"),
):
    """Run LLM deep analysis on a gene using all available evidence."""
    from openlab.db.models.evidence import Evidence
    from openlab.services import llm_service

    db = _SessionLocal()
    try:
        gene = gene_service.get_gene_by_locus(db, locus_tag)

        evidence_rows = (
            db.query(Evidence)
            .filter(Evidence.gene_id == gene.gene_id)
            .order_by(Evidence.evidence_type, Evidence.evidence_id)
            .all()
        )

        if not evidence_rows:
            console.print(f"[yellow]No evidence found for {locus_tag}. Run the pipeline first.[/yellow]")
            raise typer.Exit(code=1)

        prompt = _build_prompt(gene, evidence_rows)

        if prompt_only:
            console.print(Panel(prompt, title="LLM Prompt", border_style="blue"))
            return

        console.print(f"[cyan]Analyzing {locus_tag} with {len(evidence_rows)} evidence records...[/cyan]")
        console.print(f"[dim]Provider: {llm_service.settings.llm_provider} / {llm_service.settings.llm_model}[/dim]\n")

        with console.status("Thinking..."):
            response = llm_service.synthesize(
                prompt, purpose="gene_synthesis", gene_locus_tag=locus_tag,
            )

        console.print(Panel(
            Markdown(response),
            title=f"LLM Analysis: {locus_tag}",
            border_style="green",
        ))

        save = typer.confirm("\nSave this as a hypothesis?", default=False)
        if save:
            confidence = _extract_confidence(response)
            evidence_ids = [ev.evidence_id for ev in evidence_rows]
            hyp = hypothesis_service.create_hypothesis(
                db=db,
                title=f"Predicted function for {locus_tag}",
                description=response,
                confidence_score=confidence,
                evidence_ids=evidence_ids,
                gene_id=gene.gene_id,
            )
            console.print(f"[green]Saved hypothesis #{hyp.hypothesis_id} (confidence={confidence:.2f})[/green]")

    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1)
    finally:
        db.close()


@app.command(name="batch")
def batch_cmd(
    limit: int = typer.Option(10, help="Max genes to analyze"),
    unknown_only: bool = typer.Option(True, "--unknown-only/--all", help="Only analyze unknown-function genes"),
    save: bool = typer.Option(True, "--save/--no-save", help="Save hypotheses to DB"),
):
    """Batch LLM analysis on multiple genes."""
    from openlab.db.models.evidence import Evidence
    from openlab.services import llm_service

    db = _SessionLocal()
    try:
        genes = gene_service.list_genes(db, unknown_only=unknown_only, limit=500)

        candidates = []
        for gene in genes:
            existing = hypothesis_service.get_hypothesis_for_gene(db, gene.gene_id)
            if not existing:
                candidates.append(gene)
            if len(candidates) >= limit:
                break

        if not candidates:
            console.print("[yellow]All genes already have hypotheses.[/yellow]")
            return

        console.print(f"[cyan]Analyzing {len(candidates)} genes without hypotheses...[/cyan]\n")

        results = Table(title="Batch Analysis Results")
        results.add_column("Locus Tag", style="cyan")
        results.add_column("Evidence", justify="right")
        results.add_column("Confidence", justify="right")
        results.add_column("Status")

        for i, gene in enumerate(candidates, 1):
            evidence_rows = (
                db.query(Evidence)
                .filter(Evidence.gene_id == gene.gene_id)
                .order_by(Evidence.evidence_type)
                .all()
            )

            if not evidence_rows:
                results.add_row(gene.locus_tag, "0", "-", "[yellow]no evidence[/yellow]")
                continue

            console.print(f"[{i}/{len(candidates)}] {gene.locus_tag} ({len(evidence_rows)} evidence)...", end=" ")

            try:
                prompt = _build_prompt(gene, evidence_rows)
                response = llm_service.synthesize(
                    prompt, purpose="batch_synthesis", gene_locus_tag=gene.locus_tag,
                )
                confidence = _extract_confidence(response)

                if save:
                    evidence_ids = [ev.evidence_id for ev in evidence_rows]
                    hypothesis_service.create_hypothesis(
                        db=db,
                        title=f"Predicted function for {gene.locus_tag}",
                        description=response,
                        confidence_score=confidence,
                        evidence_ids=evidence_ids,
                        gene_id=gene.gene_id,
                    )

                console.print(f"[green]conf={confidence:.2f}[/green]")
                results.add_row(
                    gene.locus_tag,
                    str(len(evidence_rows)),
                    f"{confidence:.2f}",
                    "[green]saved[/green]" if save else "[blue]analyzed[/blue]",
                )
            except Exception as exc:
                console.print(f"[red]error: {exc}[/red]")
                results.add_row(gene.locus_tag, str(len(evidence_rows)), "-", "[red]error[/red]")

        console.print()
        console.print(results)

    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1)
    finally:
        db.close()


@app.command(name="status")
def status_cmd():
    """Show pipeline status: evidence coverage and hypothesis stats."""
    from openlab.db.models.evidence import Evidence, EvidenceType
    from openlab.db.models.hypothesis import Hypothesis, HypothesisStatus
    from sqlalchemy import func

    db = _SessionLocal()
    try:
        total_genes = db.query(Gene).count()
        unknown_genes = len(gene_service.list_genes(db, unknown_only=True, limit=9999))
        total_evidence = db.query(Evidence).count()
        total_hypotheses = db.query(Hypothesis).count()

        type_counts = (
            db.query(Evidence.evidence_type, func.count())
            .group_by(Evidence.evidence_type)
            .all()
        )

        status_counts = (
            db.query(Hypothesis.status, func.count())
            .group_by(Hypothesis.status)
            .all()
        )

        from openlab.services.gene_service import genes_without_evidence
        unannotated = genes_without_evidence(db)

        console.print(Panel(
            f"[bold]Total genes:[/bold] {total_genes}\n"
            f"[bold]Unknown function:[/bold] {unknown_genes}\n"
            f"[bold]Without evidence:[/bold] {len(unannotated)}\n"
            f"[bold]Evidence records:[/bold] {total_evidence}\n"
            f"[bold]Hypotheses:[/bold] {total_hypotheses}",
            title="Pipeline Status",
            border_style="cyan",
        ))

        if type_counts:
            t = Table(title="Evidence by Type")
            t.add_column("Type", style="yellow")
            t.add_column("Count", justify="right")
            for etype, count in sorted(type_counts, key=lambda x: -x[1]):
                t.add_row(etype.value, str(count))
            console.print(t)

        if status_counts:
            t = Table(title="Hypotheses by Status")
            t.add_column("Status", style="green")
            t.add_column("Count", justify="right")
            for status, count in status_counts:
                t.add_row(status.value, str(count))
            console.print(t)

        if unannotated:
            console.print(f"\n[yellow]Genes needing pipeline run:[/yellow]")
            for g in unannotated[:20]:
                console.print(f"  {g.locus_tag}")
            if len(unannotated) > 20:
                console.print(f"  ... and {len(unannotated) - 20} more")

    finally:
        db.close()


@app.command(name="convergence")
def convergence_cmd(
    limit: int = typer.Option(100, help="Max results to display"),
    min_score: float = typer.Option(0.0, help="Minimum convergence score to show"),
):
    """Compute and display convergence scores for all hypotheses."""
    from openlab.services import validation_service

    db = _SessionLocal()
    try:
        with console.status("Computing convergence scores..."):
            results = validation_service.compute_all_convergence(db)

        if not results:
            console.print("[yellow]No hypotheses with gene links found.[/yellow]")
            return

        results = [r for r in results if r["convergence_score"] >= min_score]
        results.sort(key=lambda r: -r["convergence_score"])
        results = results[:limit]

        table = Table(title=f"Convergence Scores ({len(results)} genes)")
        table.add_column("Locus Tag", style="cyan")
        table.add_column("Convergence", justify="right")
        table.add_column("Confidence", justify="right")
        table.add_column("Agreement")

        for r in results:
            conv = r["convergence_score"]
            conf = r["confidence_score"]
            if conv >= 0.8:
                color = "green"
                label = "Strong"
            elif conv >= 0.5:
                color = "yellow"
                label = "Moderate"
            else:
                color = "red"
                label = "Weak"

            table.add_row(
                r["locus_tag"],
                f"{conv:.3f}",
                f"{conf:.2f}" if conf is not None else "\u2014",
                f"[{color}]{label}[/{color}]",
            )

        console.print(table)

        avg_conv = sum(r["convergence_score"] for r in results) / len(results)
        strong = sum(1 for r in results if r["convergence_score"] >= 0.8)
        console.print(
            f"\n[bold]Mean convergence:[/bold] {avg_conv:.3f}  |  "
            f"[bold]Strong agreement (\u22650.8):[/bold] {strong}/{len(results)}"
        )

    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1)
    finally:
        db.close()


@app.command(name="validate")
def validate_cmd(
    output_json: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Run leave-one-out validation on genes with curated reclassifications."""
    from openlab.services import validation_service

    db = _SessionLocal()
    try:
        console.print("[cyan]Running leave-one-out validation...[/cyan]")
        console.print(
            "[dim]This calls the LLM for each curated gene \u2014 may take a few minutes.[/dim]\n"
        )

        results = validation_service.leave_one_out(db)

        if not results:
            console.print("[yellow]No genes with curated reclassifications found.[/yellow]")
            return

        if output_json:
            typer.echo(json.dumps(results, indent=2, default=str))
            return

        table = Table(title=f"Leave-One-Out Validation ({len(results)} genes)")
        table.add_column("Locus Tag", style="cyan")
        table.add_column("Curated Function")
        table.add_column("Predicted Function")
        table.add_column("Match", justify="right")
        table.add_column("Conf", justify="right")
        table.add_column("Pass")

        passed = 0
        for r in results:
            is_pass = r["passed"]
            if is_pass:
                passed += 1
            table.add_row(
                r["locus_tag"],
                r["curated_function"][:40],
                r["predicted_function"][:40],
                f"{r['match_score']:.2f}",
                f"{r['confidence']:.2f}",
                "[green]PASS[/green]" if is_pass else "[red]FAIL[/red]",
            )

        console.print(table)

        accuracy = passed / len(results) if results else 0
        console.print(
            f"\n[bold]Accuracy:[/bold] {passed}/{len(results)} "
            f"({accuracy:.0%})  |  "
            f"[bold]Threshold:[/bold] match_score \u2265 0.3"
        )

    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1)
    finally:
        db.close()


@app.command(name="validate-all")
def validate_all_cmd(
    bootstrap: bool = typer.Option(False, "--bootstrap", help="Run bootstrap stability analysis"),
    bootstrap_limit: int = typer.Option(20, help="Max genes for bootstrap (slow)"),
    export: str = typer.Option(None, "--export", help="Export full report to JSON file"),
    output_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
):
    """Run combined validation: ortholog + consistency + optional bootstrap."""
    from openlab.services import validation_service

    db = _SessionLocal()
    try:
        with console.status("Running validation..."):
            report = validation_service.validate_all(
                db,
                run_bootstrap=bootstrap,
                bootstrap_limit=bootstrap_limit,
            )

        if output_json:
            typer.echo(json.dumps(report, indent=2, default=str))
            if export:
                with open(export, "w") as f:
                    json.dump(report, f, indent=2, default=str)
                console.print(f"[green]Report exported to {export}[/green]")
            return

        summary = report["summary"]

        console.print(Panel(
            f"[bold]Ortholog accuracy:[/bold] {summary['ortholog_accuracy']:.1%} "
            f"({report['ortholog']['n_passed']}/{report['ortholog']['n_tested']})\n"
            f"[bold]Consistency rate:[/bold]  {summary['consistency_rate']:.1%} "
            f"({report['consistency']['n_consistent']}/{report['consistency']['n_tested']})\n"
            f"[bold]Estimated FPR:[/bold]     {summary['estimated_fpr']:.1%}",
            title="Validation Summary",
            border_style="cyan",
        ))

        orth_failures = [r for r in report["ortholog"]["results"] if not r["passed"]]
        if orth_failures:
            table = Table(title=f"Ortholog Mismatches ({len(orth_failures)})")
            table.add_column("Locus Tag", style="cyan")
            table.add_column("Proposed Function")
            table.add_column("Ortholog Function")
            table.add_column("Score", justify="right")

            for r in orth_failures[:20]:
                table.add_row(
                    r["locus_tag"],
                    r["proposed_function"][:40],
                    r["ortholog_function"][:40],
                    f"{r['combined_score']:.2f}",
                )
            console.print(table)

        cons_failures = [r for r in report["consistency"]["results"] if not r["consistent"]]
        if cons_failures:
            table = Table(title=f"Inconsistent Predictions ({len(cons_failures)})")
            table.add_column("Locus Tag", style="cyan")
            table.add_column("Proposed")
            table.add_column("Proposed Cat")
            table.add_column("Evidence Majority")

            for r in cons_failures[:20]:
                table.add_row(
                    r["locus_tag"],
                    r["proposed_function"][:30],
                    ", ".join(r["proposed_categories"]) or "\u2014",
                    ", ".join(r["evidence_majority_categories"]),
                )
            console.print(table)

        if "bootstrap" in report:
            boot = report["bootstrap"]
            console.print(f"\n[bold]Bootstrap stability:[/bold] "
                          f"{boot['n_stable']}/{boot['n_tested']} stable (std < 0.15)")

        if export:
            with open(export, "w") as f:
                json.dump(report, f, indent=2, default=str)
            console.print(f"\n[green]Full report exported to {export}[/green]")

    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1)
    finally:
        db.close()


@app.command(name="disagreements")
def disagreements_cmd(
    locus_tag: str = typer.Argument(None, help="Locus tag (omit for batch mode)"),
    threshold: float = typer.Option(0.2, help="Agreement score threshold for disagreement"),
    output_json: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Detect disagreements between evidence sources."""
    db = _SessionLocal()
    try:
        if locus_tag:
            gene = gene_service.get_gene_by_locus(db, locus_tag)
            report = gene_service.detect_disagreements(db, gene.gene_id, threshold)

            if output_json:
                data = {
                    "gene_id": report.gene_id,
                    "convergence_score": report.convergence_score,
                    "total_pairs": report.total_pairs,
                    "disagreeing_pairs": [
                        {
                            "source_a": dp.source_a,
                            "source_b": dp.source_b,
                            "agreement_score": dp.agreement_score,
                            "categories_a": sorted(dp.categories_a),
                            "categories_b": sorted(dp.categories_b),
                        }
                        for dp in report.disagreeing_pairs
                    ],
                }
                typer.echo(json.dumps(data, indent=2))
                return

            console.print(Panel(
                f"[bold]{locus_tag}[/bold]  "
                f"Convergence: {report.convergence_score:.3f}  |  "
                f"Total pairs: {report.total_pairs}  |  "
                f"Disagreements: {len(report.disagreeing_pairs)}",
                title="Disagreement Report",
                border_style="red" if report.disagreeing_pairs else "green",
            ))

            if not report.disagreeing_pairs:
                console.print("[green]No disagreements found \u2014 evidence is consistent.[/green]")
                return

            table = Table(title="Disagreeing Evidence Pairs")
            table.add_column("Source A", style="cyan")
            table.add_column("Source B", style="yellow")
            table.add_column("Score", justify="right")
            table.add_column("Categories A")
            table.add_column("Categories B")

            for dp in report.disagreeing_pairs:
                table.add_row(
                    f"{dp.source_a} ({dp.evidence_type_a})",
                    f"{dp.source_b} ({dp.evidence_type_b})",
                    f"{dp.agreement_score:.3f}",
                    ", ".join(sorted(dp.categories_a)) or "\u2014",
                    ", ".join(sorted(dp.categories_b)) or "\u2014",
                )

            console.print(table)

        else:
            with console.status("Scanning all genes for disagreements..."):
                results = gene_service.detect_all_disagreements(db, threshold)

            if not results:
                console.print("[green]No disagreements found across all genes.[/green]")
                return

            if output_json:
                typer.echo(json.dumps(results, indent=2))
                return

            table = Table(title=f"Genes with Disagreements ({len(results)} genes)")
            table.add_column("Locus Tag", style="cyan")
            table.add_column("Convergence", justify="right")
            table.add_column("Disagreements", justify="right", style="red")
            table.add_column("Total Pairs", justify="right")
            table.add_column("Top Conflict")

            for r in results[:50]:
                table.add_row(
                    r["locus_tag"],
                    f"{r['convergence_score']:.3f}",
                    str(r["disagreement_count"]),
                    str(r["total_pairs"]),
                    r["top_disagreement"],
                )

            console.print(table)
            console.print(f"\n[bold]Total genes with disagreements:[/bold] {len(results)}")

    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1)
    finally:
        db.close()


@app.command(name="tiers")
def tiers_cmd(
    export: str = typer.Option(None, "--export", help="Export tier report to JSON file"),
    output_json: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
):
    """Categorize graduated genes into confidence tiers."""
    from openlab.services import validation_service

    db = _SessionLocal()
    try:
        with console.status("Building confidence tiers..."):
            report = validation_service.build_confidence_tiers(db)

        if output_json:
            typer.echo(json.dumps(report, indent=2, default=str))
            if export:
                with open(export, "w") as f:
                    json.dump(report, f, indent=2, default=str)
                console.print(f"[green]Exported to {export}[/green]")
            return

        summary = report["summary"]

        tier_info = summary["tier_breakdown"]
        console.print(Panel(
            f"[bold]Total graduated:[/bold] {summary['total_graduated']}\n"
            f"[bold green]Tier 1 (High):[/bold green]     {tier_info.get('1', {}).get('count', 0)}  "
            f"(mean conv={tier_info.get('1', {}).get('mean_convergence', 0):.3f})\n"
            f"[bold yellow]Tier 2 (Moderate):[/bold yellow] {tier_info.get('2', {}).get('count', 0)}  "
            f"(mean conv={tier_info.get('2', {}).get('mean_convergence', 0):.3f})\n"
            f"[bold]Tier 3 (Low):[/bold]      {tier_info.get('3', {}).get('count', 0)}  "
            f"(mean conv={tier_info.get('3', {}).get('mean_convergence', 0):.3f})\n"
            f"[bold red]Tier 4 (Flagged):[/bold red]  {tier_info.get('4', {}).get('count', 0)}  "
            f"(mean conv={tier_info.get('4', {}).get('mean_convergence', 0):.3f})",
            title="Confidence Tiers",
            border_style="cyan",
        ))

        tier_names = {
            "1": ("High", "green"),
            "2": ("Moderate", "yellow"),
            "3": ("Low", "white"),
            "4": ("Flagged", "red"),
        }

        for tier_num in ["1", "2", "3", "4"]:
            genes = report["tiers"].get(tier_num, [])
            if not genes:
                continue
            name, color = tier_names[tier_num]

            table = Table(title=f"Tier {tier_num} \u2014 {name} ({len(genes)} genes)")
            table.add_column("Locus Tag", style="cyan")
            table.add_column("Proposed Function")
            table.add_column("Conv", justify="right")
            table.add_column("Conf", justify="right")
            table.add_column("Ev#", justify="right")
            table.add_column("Orth")
            table.add_column("Cons")

            for g in sorted(genes, key=lambda x: -x["convergence_score"])[:30]:
                orth_str = (
                    "[green]Y[/green]" if g["ortholog_passed"] is True
                    else "[red]N[/red]" if g["ortholog_passed"] is False
                    else "\u2014"
                )
                cons_str = "[green]Y[/green]" if g["consistency_passed"] else "[red]N[/red]"
                table.add_row(
                    g["locus_tag"],
                    (g["proposed_function"] or "")[:45],
                    f"{g['convergence_score']:.3f}",
                    f"{g['confidence_score']:.2f}",
                    str(g["evidence_count"]),
                    orth_str,
                    cons_str,
                )

            console.print(table)

        if export:
            with open(export, "w") as f:
                json.dump(report, f, indent=2, default=str)
            console.print(f"\n[green]Full report exported to {export}[/green]")

    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1)
    finally:
        db.close()


def _format_evidence(etype: str, payload: dict) -> str:
    """Format evidence payload for display."""
    source = payload.get("source", "")

    if etype == "HOMOLOGY":
        hits = payload.get("hits", [])
        if hits:
            first = hits[0]
            parts = []
            if first.get("accession"):
                parts.append(first["accession"])
            if first.get("description"):
                parts.append(first["description"][:60])
            if first.get("evalue") is not None:
                parts.append(f"E={first['evalue']}")
            if first.get("identity_pct"):
                parts.append(f"{first['identity_pct']}% id")
            more = f" (+{len(hits)-1} more)" if len(hits) > 1 else ""
            return ", ".join(parts) + more
        if payload.get("protein_name"):
            return f"{payload.get('accession', '')} {payload['protein_name']}"

    elif etype == "STRUCTURE":
        if source == "Foldseek":
            hits = payload.get("hits", [])
            if hits:
                return f"top hit: {hits[0].get('target', '?')} TM={hits[0].get('tm_score', '?')}"
        elif source == "ESMFold":
            return f"avg pLDDT={payload.get('avg_plddt', '?')}"
        elif source == "AlphaFold":
            return f"structure for {payload.get('uniprot_accession', '?')}"

    elif etype == "COMPUTATIONAL":
        if source == "InterProScan":
            matches = payload.get("matches", [])
            if matches:
                return f"{len(matches)} domain matches"
        elif source == "STRING":
            partners = payload.get("partners", [])
            return f"{len(partners)} interaction partners"
        elif source == "eggNOG":
            return f"COG={payload.get('cog_category', '?')} {payload.get('predicted_name', '')}"
        elif source == "DeepTMHMM":
            return f"topology={payload.get('topology', '?')} TM={payload.get('n_tm_helices', 0)}"
        elif source == "SignalP6":
            return f"{payload.get('sp_type', 'none')} cleavage={payload.get('cleavage_site', '?')}"

    elif etype == "TRANSPOSON":
        return f"{payload.get('essentiality', '?')} (class={payload.get('tn5_class', '?')})"

    elif etype == "LITERATURE":
        articles = payload.get("articles", [])
        if articles:
            return f"{len(articles)} papers, latest: {articles[0].get('title', '')[:50]}"

    return json.dumps(payload, default=str)[:100]
