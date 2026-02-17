"""Verification page — validation results, convergence histograms, calibration."""

import streamlit as st


def render():
    st.title("Verification & Validation")

    from dashboard.data import get_validation_summary, get_confidence_tiers, get_hypotheses_df

    # Validation summary
    summary = get_validation_summary()
    if summary:
        col1, col2, col3 = st.columns(3)
        col1.metric("Ortholog Accuracy", f"{summary.get('ortholog_accuracy', 0):.1%}")
        col2.metric("Consistency Rate", f"{summary.get('consistency_rate', 0):.1%}")
        col3.metric("Estimated FPR", f"{summary.get('estimated_fpr', 0):.1%}")
    else:
        st.info("No validation data yet. Run `biolab validate all` first.")

    st.divider()

    # Confidence tiers
    st.subheader("Confidence Tiers")
    tiers = get_confidence_tiers()
    tier_summary = tiers.get("summary", {}).get("tier_breakdown", {})

    if tier_summary:
        import plotly.express as px

        tier_data = {
            "Tier": [],
            "Count": [],
            "Mean Convergence": [],
        }
        tier_labels = {"1": "High", "2": "Moderate", "3": "Low", "4": "Flagged"}
        tier_colors = {"1": "#2ecc71", "2": "#f39c12", "3": "#95a5a6", "4": "#e74c3c"}

        for tier_num in ["1", "2", "3", "4"]:
            info = tier_summary.get(tier_num, {"count": 0, "mean_convergence": 0})
            tier_data["Tier"].append(f"Tier {tier_num}: {tier_labels.get(tier_num, '?')}")
            tier_data["Count"].append(info["count"])
            tier_data["Mean Convergence"].append(info["mean_convergence"])

        col1, col2 = st.columns(2)

        with col1:
            fig = px.bar(
                x=tier_data["Tier"], y=tier_data["Count"],
                color=tier_data["Tier"],
                title="Genes per Confidence Tier",
            )
            fig.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.bar(
                x=tier_data["Tier"], y=tier_data["Mean Convergence"],
                color=tier_data["Tier"],
                title="Mean Convergence by Tier",
            )
            fig.update_layout(height=350, showlegend=False, yaxis_range=[0, 1])
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Convergence histogram
    st.subheader("Convergence Score Distribution")
    hyps = get_hypotheses_df()
    if hyps:
        import pandas as pd
        import plotly.express as px

        df = pd.DataFrame(hyps)

        fig = px.histogram(
            df, x="convergence_score",
            nbins=25,
            title="Distribution of Convergence Scores",
            labels={"convergence_score": "Convergence Score"},
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

        # Calibration: confidence vs convergence binned
        st.subheader("Calibration: Confidence vs Convergence")
        df["conv_bin"] = pd.cut(df["convergence_score"], bins=5, labels=False)
        cal_df = df.groupby("conv_bin").agg(
            mean_confidence=("confidence_score", "mean"),
            mean_convergence=("convergence_score", "mean"),
            count=("hypothesis_id", "count"),
        ).reset_index()

        fig = px.scatter(
            cal_df, x="mean_convergence", y="mean_confidence",
            size="count",
            title="Calibration: Mean Confidence by Convergence Bin",
            labels={
                "mean_convergence": "Mean Convergence",
                "mean_confidence": "Mean Confidence",
            },
        )
        # Add perfect calibration line
        fig.add_shape(
            type="line", x0=0, y0=0, x1=1, y1=1,
            line=dict(dash="dash", color="gray"),
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
