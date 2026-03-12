"""Map page - Search and interactive map."""

import streamlit as st
from streamlit_folium import st_folium
import folium

from lib.geocoding import search_places, format_address

# Default: Tel Aviv
DEFAULT_LAT = 32.0853
DEFAULT_LNG = 34.7818
DEFAULT_ZOOM = 10

st.set_page_config(page_title="Map", page_icon="🗺️", layout="wide")

st.title("Map")
st.caption("Search for streets, cities, and addresses. Powered by OpenStreetMap.")

# Search
query = st.text_input("חיפוש רחוב, עיר, כתובת...", placeholder="e.g. Tel Aviv, Jerusalem, Dizengoff")
results = []
if query:
    try:
        results = search_places(query, limit=6)
    except Exception as e:
        st.error(f"Search failed: {e}")

# Selection
selected = None
if results:
    options = [format_address(f) for f in results]
    idx = st.selectbox("Select result", range(len(options)), format_func=lambda i: options[i])
    if idx is not None:
        selected = results[idx]

# Map center
if selected:
    coords = selected.get("geometry", {}).get("coordinates", [DEFAULT_LNG, DEFAULT_LAT])
    lng, lat = coords[0], coords[1]
    zoom = 15
else:
    lat, lng, zoom = DEFAULT_LAT, DEFAULT_LNG, DEFAULT_ZOOM

# Folium map
m = folium.Map(location=[lat, lng], zoom_start=zoom, tiles="OpenStreetMap")
if selected:
    folium.Marker([lat, lng], popup=format_address(selected)).add_to(m)

st_folium(m, width=None, height=500)
