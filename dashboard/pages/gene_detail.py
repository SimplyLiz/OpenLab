"""Gene Detail page — per-gene evidence, structure viewer, sequences."""

import streamlit as st


def render():
    st.title("Gene Detail")

    from dashboard.data import get_genes_df, get_gene_detail

    genes = get_genes_df()
    if not genes:
        st.info("No genes in database.")
        return

    locus_tags = [g["locus_tag"] for g in genes]
    selected = st.selectbox("Select gene", locus_tags)

    if not selected:
        return

    gene_id = next(g["gene_id"] for g in genes if g["locus_tag"] == selected)
    detail = get_gene_detail(gene_id)

    if not detail:
        st.error("Could not load gene details.")
        return

    # Gene info
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(f"{detail['locus_tag']}")
        st.write(f"**Product:** {detail['product'] or 'hypothetical protein'}")
        st.write(f"**Name:** {detail.get('name', '-')}")
        st.write(f"**Essentiality:** {detail.get('essentiality', 'unknown')}")
        st.write(f"**Evidence records:** {detail['evidence_count']}")

    with col2:
        if detail.get("proposed_function"):
            st.success(f"**Proposed function:** {detail['proposed_function']}")
        if detail.get("graduated_at"):
            st.info(f"Graduated: {detail['graduated_at']}")

    st.divider()

    # Evidence by type
    st.subheader("Evidence")
    for etype, records in detail.get("evidence_by_type", {}).items():
        with st.expander(f"{etype} ({len(records)} records)", expanded=len(records) <= 3):
            for rec in records:
                payload = rec.get("payload", {})
                source = payload.get("source", "?")
                conf = rec.get("confidence")
                conf_str = f" | confidence: {conf:.2f}" if conf is not None else ""
                st.markdown(f"**{source}**{conf_str}")
                st.json(payload, expanded=False)

    # Protein features
    features = detail.get("features", [])
    if features:
        st.subheader("Protein Features")
        import pandas as pd
        feat_df = pd.DataFrame(features)
        st.dataframe(feat_df, use_container_width=True)

    # Structure viewer
    st.subheader("Structure")
    from pathlib import Path
    from biolab.config import config

    struct_dir = Path(config.tools.structure_dir)
    pdb_path = None
    for suffix in ("_esmfold.pdb", "_alphafold.pdb"):
        candidate = struct_dir / f"{selected}{suffix}"
        if candidate.exists():
            pdb_path = candidate
            break

    if pdb_path:
        try:
            from streamlit_molstar import st_molstar
            pdb_text = pdb_path.read_text()
            st_molstar(pdb_text, key=f"mol_{selected}", height=400)
        except ImportError:
            st.code(f"PDB file: {pdb_path}", language="text")
            st.info("Install streamlit-molstar for 3D structure visualization.")
    else:
        st.info("No structure file available. Run ESMFold or AlphaFold first.")
