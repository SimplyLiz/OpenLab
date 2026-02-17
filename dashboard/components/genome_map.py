"""Circular genome map using pycirclize."""

from __future__ import annotations

import streamlit as st


def render_genome_map(genes: list[dict]):
    """Render a circular genome map using pycirclize."""
    try:
        from pycirclize import Circos
        import matplotlib.pyplot as plt
    except ImportError:
        st.warning("Install pycirclize for circular genome visualization: pip install pycirclize")
        return

    if not genes:
        return

    genome_size = max(g["end"] for g in genes) if genes else 543000

    circos = Circos(
        sectors={"syn3A": genome_size},
        space=0,
    )

    sector = circos.sectors[0]

    # Gene track
    track = sector.add_track((90, 100))
    track.axis(fc="lightgray", ec="none")

    for gene in genes:
        start = gene["start"]
        end = gene["end"]
        strand = 1 if gene["strand"] == "+" else -1

        # Color by status
        if gene.get("graduated"):
            color = "#2ecc71"  # green
        elif gene.get("proposed_function"):
            color = "#f39c12"  # orange
        elif "hypothetical" in (gene.get("product") or "").lower():
            color = "#e74c3c"  # red
        else:
            color = "#3498db"  # blue

        if strand == 1:
            track.rect(start, end, fc=color, ec="none", lw=0)
        else:
            # Inner track for minus strand
            pass

    # Inner track for minus strand genes
    track_inner = sector.add_track((78, 88))
    track_inner.axis(fc="lightgray", ec="none")

    for gene in genes:
        if gene["strand"] == "-":
            start = gene["start"]
            end = gene["end"]

            if gene.get("graduated"):
                color = "#2ecc71"
            elif "hypothetical" in (gene.get("product") or "").lower():
                color = "#e74c3c"
            else:
                color = "#3498db"

            track_inner.rect(start, end, fc=color, ec="none", lw=0)

    fig = circos.plotfig()
    st.pyplot(fig)
    plt.close(fig)
