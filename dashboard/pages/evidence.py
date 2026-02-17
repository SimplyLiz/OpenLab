"""Evidence page — distribution charts and coverage matrix."""

import streamlit as st


def render():
    st.title("Evidence Analysis")

    from dashboard.data import get_evidence_by_type, get_evidence_by_source, get_genes_df, get_gene_evidence_counts

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Evidence by Type")
        ev_by_type = get_evidence_by_type()
        if ev_by_type:
            import plotly.express as px
            fig = px.bar(
                x=list(ev_by_type.keys()),
                y=list(ev_by_type.values()),
                labels={"x": "Type", "y": "Count"},
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Evidence by Source")
        ev_by_source = get_evidence_by_source()
        if ev_by_source:
            import plotly.express as px
            sorted_sources = sorted(ev_by_source.items(), key=lambda x: -x[1])
            fig = px.bar(
                x=[s[0] for s in sorted_sources],
                y=[s[1] for s in sorted_sources],
                labels={"x": "Source", "y": "Count"},
            )
            fig.update_layout(height=350, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

    # Coverage matrix
    st.subheader("Evidence Coverage Matrix")
    genes = get_genes_df()
    ev_counts = get_gene_evidence_counts()

    if genes:
        import pandas as pd

        df = pd.DataFrame(genes)
        df["evidence_count"] = df["gene_id"].map(ev_counts).fillna(0).astype(int)

        # Coverage summary
        total = len(df)
        with_evidence = (df["evidence_count"] > 0).sum()
        rich_evidence = (df["evidence_count"] >= 5).sum()

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Genes", total)
        col2.metric("With Evidence", f"{with_evidence} ({with_evidence/total*100:.0f}%)" if total else "0")
        col3.metric("Rich Evidence (5+)", f"{rich_evidence} ({rich_evidence/total*100:.0f}%)" if total else "0")

        # Histogram
        import plotly.express as px
        fig = px.histogram(
            df, x="evidence_count",
            nbins=20,
            title="Distribution of Evidence Counts per Gene",
            labels={"evidence_count": "Evidence Records"},
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
