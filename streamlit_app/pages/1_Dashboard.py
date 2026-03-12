"""Dashboard page - Welcome, Stats, AI placeholder."""

import streamlit as st

from lib.api import fetch_health, fetch_layers

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

st.title("Israel Housing Dashboard")
st.caption("AI-powered real estate intelligence platform")

# Welcome Hero
st.markdown("---")
st.markdown("### Welcome to Israel Housing")
st.markdown(
    "Real estate intelligence platform powered by AI. Explore properties, analyze districts, and get insights with our advanced modules."
)
st.markdown("---")

# Stats Cards
col1, col2, col3 = st.columns(3)

try:
    health = fetch_health()
    is_api_available = health.get("status") == "ok"
except Exception:
    is_api_available = False
    health = {}

try:
    layers = fetch_layers() if is_api_available else []
except Exception:
    layers = []

with col1:
    st.metric(
        label="Map Layers",
        value=len(layers) if layers else "—",
        delta="Available" if layers else "Service unavailable",
    )

with col2:
    props_ready = any(l.get("id") == "properties" for l in layers) if layers else False
    st.metric(
        label="Properties",
        value="Ready" if props_ready else "—",
        delta="Property data layer",
    )

with col3:
    st.metric(
        label="API Status",
        value="Connected" if is_api_available else "Offline",
        delta="dashboard_service" if is_api_available else "Start backend on :8000",
    )

# AI Placeholder
st.markdown("---")
st.markdown("### AI Modules")
st.info("AI-powered insights, predictions, and recommendations coming soon.")
