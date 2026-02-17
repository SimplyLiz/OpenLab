"""BioLab Dashboard — Streamlit main app with page navigation."""

import streamlit as st

st.set_page_config(
    page_title="BioLab Dashboard",
    page_icon="\U0001f9ec",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("BioLab")
st.sidebar.markdown("Unified Bioinformatics Platform")

page = st.sidebar.radio(
    "Navigate",
    [
        "Overview",
        "Gene Explorer",
        "Gene Detail",
        "Evidence",
        "Hypotheses",
        "Verification",
    ],
)

if page == "Overview":
    from dashboard.pages.overview import render
    render()
elif page == "Gene Explorer":
    from dashboard.pages.gene_explorer import render
    render()
elif page == "Gene Detail":
    from dashboard.pages.gene_detail import render
    render()
elif page == "Evidence":
    from dashboard.pages.evidence import render
    render()
elif page == "Hypotheses":
    from dashboard.pages.hypotheses import render
    render()
elif page == "Verification":
    from dashboard.pages.verification import render
    render()
