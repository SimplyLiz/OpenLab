"""Hypotheses page — hypothesis list, confidence histogram."""

import streamlit as st


def render():
    st.title("Hypotheses")

    from dashboard.data import get_hypotheses_df

    hyps = get_hypotheses_df()
    if not hyps:
        st.info("No hypotheses generated yet. Run the synthesis pipeline first.")
        return

    import pandas as pd
    df = pd.DataFrame(hyps)

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Hypotheses", len(df))
    col2.metric("Mean Confidence", f"{df['confidence_score'].mean():.2f}")
    col3.metric("Mean Convergence", f"{df['convergence_score'].mean():.2f}")

    # Confidence histogram
    st.subheader("Confidence Distribution")
    import plotly.express as px
    fig = px.histogram(
        df, x="confidence_score",
        nbins=20,
        title="Hypothesis Confidence Scores",
        labels={"confidence_score": "Confidence"},
    )
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)

    # Convergence vs Confidence scatter
    st.subheader("Convergence vs Confidence")
    fig = px.scatter(
        df, x="convergence_score", y="confidence_score",
        hover_data=["title"],
        title="Evidence Convergence vs LLM Confidence",
        labels={
            "convergence_score": "Convergence Score",
            "confidence_score": "Confidence Score",
        },
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

    # Table
    st.subheader("All Hypotheses")
    st.dataframe(
        df[["hypothesis_id", "gene_id", "title", "confidence_score", "convergence_score", "status"]],
        use_container_width=True,
        height=400,
    )
