"""Reusable evidence visualization components."""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def evidence_type_pie(ev_by_type: dict[str, int]):
    """Pie chart of evidence by type."""
    if not ev_by_type:
        st.info("No evidence data.")
        return

    fig = px.pie(
        values=list(ev_by_type.values()),
        names=list(ev_by_type.keys()),
        hole=0.3,
        title="Evidence by Type",
    )
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)


def evidence_source_bar(ev_by_source: dict[str, int]):
    """Bar chart of evidence by source."""
    if not ev_by_source:
        st.info("No evidence data.")
        return

    sorted_items = sorted(ev_by_source.items(), key=lambda x: -x[1])
    fig = px.bar(
        x=[s[0] for s in sorted_items],
        y=[s[1] for s in sorted_items],
        labels={"x": "Source", "y": "Count"},
        title="Evidence by Source",
    )
    fig.update_layout(height=350, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)


def gene_evidence_bar(genes: list[dict], ev_counts: dict[int, int]):
    """Bar chart of evidence count per gene along genome position."""
    if not genes:
        return

    import pandas as pd
    df = pd.DataFrame(genes)
    df["evidence_count"] = df["gene_id"].map(ev_counts).fillna(0).astype(int)

    fig = px.bar(
        df.sort_values("start"),
        x="locus_tag", y="evidence_count",
        color="graduated",
        hover_data=["product"],
        title="Evidence per Gene (genome order)",
    )
    fig.update_layout(height=300, xaxis_tickangle=-90)
    st.plotly_chart(fig, use_container_width=True)
