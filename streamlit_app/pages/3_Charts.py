"""Charts page - Placeholder for analytics and charts."""

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Charts", page_icon="📈", layout="wide")

st.title("Charts & Analytics")
st.caption("Preparation for charts and data visualization.")

st.info("Charts and analytics coming soon. This page is prepared for future integration.")

# Demo chart with sample data
st.subheader("Sample Chart (Demo)")
df = pd.DataFrame(
    {"Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"], "Value": [10, 20, 15, 25, 30, 28]}
)
st.line_chart(df.set_index("Month"))
