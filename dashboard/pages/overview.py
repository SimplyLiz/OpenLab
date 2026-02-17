"""Overview page — key metrics, genome map, evidence distribution."""

import streamlit as st


def render():
    st.title("Genome Overview")

    from dashboard.data import (
        get_gene_count, get_evidence_count, get_hypothesis_count,
        get_graduated_count, get_evidence_by_type, get_genes_df,
    )

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Genes", get_gene_count())
    col2.metric("Evidence Records", get_evidence_count())
    col3.metric("Hypotheses", get_hypothesis_count())
    col4.metric("Graduated", get_graduated_count())

    st.divider()

    # Evidence type distribution
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Evidence by Type")
        ev_by_type = get_evidence_by_type()
        if ev_by_type:
            import plotly.express as px
            fig = px.pie(
                values=list(ev_by_type.values()),
                names=list(ev_by_type.keys()),
                hole=0.3,
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No evidence data yet.")

    with col_right:
        st.subheader("Genome Map")
        genes = get_genes_df()
        if genes:
            try:
                from dashboard.components.genome_map import render_genome_map
                render_genome_map(genes)
            except ImportError:
                # Fallback: simple bar chart of gene positions
                import plotly.express as px
                import pandas as pd
                df = pd.DataFrame(genes)
                fig = px.bar(
                    df, x="start", y="length",
                    color="essentiality",
                    hover_data=["locus_tag", "product"],
                    title="Gene Positions",
                )
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No genes imported yet.")

    # Evidence coverage bar
    st.subheader("Evidence Coverage per Gene")
    from dashboard.data import get_gene_evidence_counts
    ev_counts = get_gene_evidence_counts()
    if genes and ev_counts:
        import plotly.express as px
        import pandas as pd

        df = pd.DataFrame(genes)
        df["evidence_count"] = df["gene_id"].map(ev_counts).fillna(0).astype(int)

        fig = px.bar(
            df.sort_values("start"),
            x="locus_tag", y="evidence_count",
            color="graduated",
            hover_data=["product", "proposed_function"],
            title="Evidence Records per Gene",
        )
        fig.update_layout(height=300, xaxis_tickangle=-90, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
