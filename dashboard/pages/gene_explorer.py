"""Gene Explorer page — filterable gene table."""

import streamlit as st


def render():
    st.title("Gene Explorer")

    from dashboard.data import get_genes_df, get_gene_evidence_counts

    genes = get_genes_df()
    if not genes:
        st.info("No genes in database. Import a genome first.")
        return

    import pandas as pd

    df = pd.DataFrame(genes)
    ev_counts = get_gene_evidence_counts()
    df["evidence_count"] = df["gene_id"].map(ev_counts).fillna(0).astype(int)

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        search = st.text_input("Search (locus tag, name, product)", "")
    with col2:
        ess_filter = st.selectbox("Essentiality", ["all", "essential", "non-essential", "unknown"])
    with col3:
        grad_filter = st.selectbox("Graduation", ["all", "graduated", "not graduated"])

    # Apply filters
    if search:
        mask = (
            df["locus_tag"].str.contains(search, case=False, na=False) |
            df["name"].str.contains(search, case=False, na=False) |
            df["product"].str.contains(search, case=False, na=False)
        )
        df = df[mask]

    if ess_filter != "all":
        df = df[df["essentiality"] == ess_filter]

    if grad_filter == "graduated":
        df = df[df["graduated"]]
    elif grad_filter == "not graduated":
        df = df[~df["graduated"]]

    st.write(f"Showing {len(df)} genes")

    # Display
    st.dataframe(
        df[[
            "locus_tag", "name", "product", "start", "end", "strand",
            "essentiality", "evidence_count", "proposed_function", "graduated",
        ]],
        use_container_width=True,
        height=600,
        column_config={
            "locus_tag": st.column_config.TextColumn("Locus Tag", width="small"),
            "product": st.column_config.TextColumn("Product", width="medium"),
            "proposed_function": st.column_config.TextColumn("Proposed Function", width="medium"),
            "evidence_count": st.column_config.NumberColumn("Evidence", width="small"),
        },
    )
