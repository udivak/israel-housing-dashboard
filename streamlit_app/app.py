"""Israel Housing Dashboard - Streamlit (testing/QA)."""

import streamlit as st

st.set_page_config(
    page_title="Israel Housing",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Israel Housing Dashboard")
st.caption("Streamlit frontend for testing and QA")

st.markdown("Use the sidebar to navigate:")
st.markdown("- **Dashboard** – Overview, API status, AI placeholder")
st.markdown("- **Map** – Search and map view")
st.markdown("- **Charts** – Analytics placeholder")
