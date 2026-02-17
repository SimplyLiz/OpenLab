"""Dossier assembly — combines all agent outputs into a structured GeneDossier."""

from __future__ import annotations

from typing import Any

from openlab.agents.agent_models import (
    Claim,
    DossierSection,
    GeneDossier,
    ProvenanceEntry,
)
from openlab.agents.critic import CriticReport


def assemble_dossier(
    identity: dict[str, Any],
    literature: list[dict],
    cancer_lit: list[dict],
    sections: list[tuple[str, str, list[Claim], list[str]]],
    critic_report: CriticReport,
    provenance: list[ProvenanceEntry],
    convergence: float,
    cancer_type: str | None = None,
) -> GeneDossier:
    """Assemble all components into a GeneDossier."""
    gene_symbol = identity.get("gene_symbol", identity.get("symbol", "unknown"))

    dossier_sections = [_format_identity_section(identity)]

    for title, content, claims, call_ids in sections:
        dossier_sections.append(
            DossierSection(
                title=title,
                content=content,
                claims=claims,
                tool_calls_used=call_ids,
            )
        )

    # Add provenance section
    dossier_sections.append(_format_provenance_section(provenance))

    # Collect all claims
    all_claims = critic_report.revised_claims if critic_report.revised_claims else []
    for _, _, claims, _ in sections:
        if not critic_report.revised_claims:
            all_claims.extend(claims)

    return GeneDossier(
        gene_symbol=gene_symbol,
        ncbi_gene_id=identity.get("gene_id") or identity.get("ncbi_gene_id"),
        ensembl_id=identity.get("id") or identity.get("ensembl_id"),
        chromosome=identity.get("chromosome") or identity.get("seq_region_name"),
        cancer_type=cancer_type,
        sections=dossier_sections,
        claims=all_claims,
        provenance=provenance,
        convergence_score=convergence,
    )


def render_markdown(dossier: GeneDossier) -> str:
    """Render a GeneDossier as a full Markdown document."""
    lines = [
        f"# Gene Dossier: {dossier.gene_symbol}",
        "",
    ]

    if dossier.cancer_type:
        lines.append(f"**Cancer type**: {dossier.cancer_type}")
    if dossier.ncbi_gene_id:
        lines.append(f"**NCBI Gene ID**: {dossier.ncbi_gene_id}")
    if dossier.ensembl_id:
        lines.append(f"**Ensembl ID**: {dossier.ensembl_id}")
    if dossier.chromosome:
        lines.append(f"**Chromosome**: {dossier.chromosome}")
    lines.append(f"**Convergence score**: {dossier.convergence_score:.3f}")
    lines.append("")

    for section in dossier.sections:
        lines.append(f"## {section.title}")
        lines.append("")
        lines.append(section.content)
        lines.append("")

        if section.claims:
            lines.append("### Claims")
            lines.append("")
            for claim in section.claims:
                spec = " [SPECULATIVE]" if claim.is_speculative else ""
                cites = ", ".join(claim.citations) if claim.citations else "no citation"
                lines.append(
                    f"- {claim.claim_text} (confidence: {claim.confidence:.2f}, "
                    f"citations: {cites}){spec}"
                )
            lines.append("")

    # Summary of all claims
    if dossier.claims:
        lines.append("## All Claims Summary")
        lines.append("")
        lines.append(f"Total claims: {len(dossier.claims)}")
        valid = sum(1 for c in dossier.claims if c.citation_status.value == "valid")
        speculative = sum(1 for c in dossier.claims if c.is_speculative)
        lines.append(f"Validated citations: {valid}")
        lines.append(f"Speculative claims: {speculative}")
        lines.append("")

    return "\n".join(lines)


def render_json(dossier: GeneDossier) -> dict[str, Any]:
    """Render a GeneDossier as JSON-serializable dict."""
    return dict(dossier.model_dump(mode="json"))


def _format_identity_section(identity: dict[str, Any]) -> DossierSection:
    lines = ["| Field | Value |", "|-------|-------|"]
    display_keys = [
        ("gene_symbol", "Gene Symbol"),
        ("gene_id", "NCBI Gene ID"),
        ("id", "Ensembl ID"),
        ("description", "Description"),
        ("chromosome", "Chromosome"),
        ("seq_region_name", "Chromosomal Region"),
        ("biotype", "Biotype"),
        ("organism", "Organism"),
    ]
    for key, label in display_keys:
        val = identity.get(key)
        if val:
            lines.append(f"| {label} | {val} |")

    return DossierSection(title="Gene Identity", content="\n".join(lines))


def _format_provenance_section(provenance: list[ProvenanceEntry]) -> DossierSection:
    lines = [
        "| Tool | Duration (ms) | Success | Sources |",
        "|------|---------------|---------|---------|",
    ]
    for entry in provenance:
        sources_str = ", ".join(entry.sources[:3]) if entry.sources else "-"
        lines.append(
            f"| {entry.tool_name} | {entry.duration_ms} | "
            f"{'Yes' if entry.success else 'No'} | {sources_str} |"
        )

    total_ms = sum(e.duration_ms for e in provenance)
    lines.append("")
    lines.append(f"**Total tool calls**: {len(provenance)}")
    lines.append(f"**Total duration**: {total_ms} ms")

    return DossierSection(
        title="Provenance",
        content="\n".join(lines),
        tool_calls_used=[e.call_id for e in provenance],
    )
