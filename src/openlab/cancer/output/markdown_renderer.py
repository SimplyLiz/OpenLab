"""Markdown report renderer for variant interpretation results."""

from __future__ import annotations

from openlab.cancer.models.variant import (
    ClinicalSignificance,
    VariantReport,
)

_DISCLAIMER = (
    "FOR RESEARCH USE ONLY. This is not a validated clinical"
    " diagnostic tool. Do not use for clinical decision-making."
)


def render_markdown(report: VariantReport) -> str:
    """Render a variant report as Markdown."""
    lines: list[str] = []

    # Header disclaimer (hardcoded, not from variable)
    lines.append(f"> **{_DISCLAIMER}**")
    lines.append("")

    # Title
    lines.append("# Variant Interpretation Report")
    lines.append("")

    # Summary
    if report.sample_id:
        lines.append(f"**Sample:** {report.sample_id}")
    if report.tumor_type:
        lines.append(f"**Tumor Type:** {report.tumor_type}")
    lines.append(f"**Genome Build:** {report.genome_build.value}")
    lines.append(f"**Total Variants Parsed:** {report.total_variants_parsed}")
    lines.append(f"**Annotated:** {report.total_annotated}")
    lines.append(f"**Pathogenic/Likely Pathogenic:** {report.total_pathogenic}")
    lines.append(f"**Actionable:** {report.total_actionable}")
    lines.append("")

    if report.summary:
        lines.append("## Summary")
        lines.append(report.summary)
        lines.append("")

    # Variant table
    if report.variants:
        lines.append("## Variants")
        lines.append("")
        lines.append("| Gene | Variant | Classification | Confidence | Actionable | Sources |")
        lines.append("|------|---------|---------------|------------|------------|---------|")

        for av in report.variants:
            v = av.variant
            variant_str = v.hgvs_p or v.hgvs_c or v.hgvs_g or f"{v.chrom}:{v.pos} {v.ref}>{v.alt}"
            cls_str = _format_classification(av.consensus_classification)
            conf_str = f"{av.confidence:.0%}"
            action_str = "Yes" if av.is_actionable else "No"
            sources_str = ", ".join(av.annotation_sources)
            lines.append(
                f"| {v.gene_symbol} | {variant_str} | {cls_str}"
                f" | {conf_str} | {action_str} | {sources_str} |"
            )

        lines.append("")

        # Detailed evidence per variant
        lines.append("## Detailed Evidence")
        lines.append("")
        for av in report.variants:
            if not av.evidence:
                continue
            v = av.variant
            variant_str = v.hgvs_p or v.hgvs_g or f"{v.chrom}:{v.pos}"
            lines.append(f"### {v.gene_symbol} {variant_str}")
            lines.append("")
            for ev in av.evidence:
                lines.append(f"- **{ev.source}**: {ev.description}")
                if ev.pmids:
                    pmid_links = ", ".join(f"PMID:{p}" for p in ev.pmids)
                    lines.append(f"  - Citations: {pmid_links}")
                if ev.therapies:
                    lines.append(f"  - Therapies: {', '.join(ev.therapies)}")
            lines.append("")

    # Footer disclaimer (hardcoded)
    lines.append("---")
    lines.append(f"> **{_DISCLAIMER}**")
    lines.append("")

    return "\n".join(lines)


def _format_classification(cls: ClinicalSignificance) -> str:
    """Format classification enum for display."""
    display_map = {
        ClinicalSignificance.PATHOGENIC: "Pathogenic",
        ClinicalSignificance.LIKELY_PATHOGENIC: "Likely Pathogenic",
        ClinicalSignificance.VUS: "VUS",
        ClinicalSignificance.LIKELY_BENIGN: "Likely Benign",
        ClinicalSignificance.BENIGN: "Benign",
    }
    return display_map.get(cls, str(cls.value))
