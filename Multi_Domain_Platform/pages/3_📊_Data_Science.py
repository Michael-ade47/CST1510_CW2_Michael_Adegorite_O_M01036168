import sys
from pathlib import Path

import streamlit as st
import plotly.express as px
import pandas as pd

# Find project root so local imports work reliably
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.database_manager import DatabaseManager
from models.dataset import (
    DatasetRepository,
    StateManager,
    AuthGuard,
    DatasetFilterPanel,
    DatasetFilter,
    DatasetOptions,
    DataScienceChat,
    build_dataset_context,
)

# Page setup
st.set_page_config(page_title="Datasets", page_icon="📁", layout="wide")

# Shared styling for banners/pills
st.markdown(
    """
    <style>
      .banner {
        padding: 14px 16px;
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,.10);
        background: linear-gradient(135deg, rgba(99,102,241,.20), rgba(16,185,129,.10));
        margin: 8px 0 14px 0;
      }
      .banner h2 { margin: 0; font-size: 22px; line-height: 1.2; }
      .banner p { margin: 6px 0 0 0; opacity: .85; }
      .pillrow { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }
      .pill {
        padding: 6px 10px;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,.12);
        background: rgba(255,255,255,.06);
        font-size: 13px;
      }
      .sectionbanner {
        padding: 10px 12px;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,.10);
        background: rgba(255,255,255,.05);
        margin: 18px 0 10px 0;
      }
      .sectionbanner strong { font-size: 14px; letter-spacing: .2px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Session defaults used across the page
StateManager(
    {
        "logged_in": False,
        "username": "",
        "role": "",
        "show_dataset_crud": False,
        "active_dataset_form": "view",
        "assistant_panel_open": False,
        "show_chart_picker": False,
        "selected_chart": "Datasets by Source (Doughnut)",
    }
).init()

st.session_state.setdefault("selected_chart", "Datasets by Source (Doughnut)")

# Require login before showing any data
AuthGuard.require_login(login_page="Home.py")

# DB + repository
db = DatabaseManager(str(ROOT / "database" / "platform.db"))
repo = DatasetRepository(db)

datasets = repo.read_all_df()
if datasets.empty:
    st.info("No datasets found in the database.")
    st.stop()

# Filters apply directly to the table
source, names = DatasetFilterPanel().render(datasets)
filtered = DatasetFilter.apply(datasets, source, names)

st.info(
    "Dataset filters are applied directly to the table. "
    "To see how filtering impacts charts, ensure the visualisations are visible."
)
st.info(
    "Any changes made using the dataset CRUD forms "
    "are reflected immediately in the datasets table."
)

st.markdown(
    f"""
    <div class="banner">
      <h2>Datasets</h2>
      <p>Manage, explore, and analyse datasets used across the platform.</p>
      <div class="pillrow">
        <div class="pill">User: <b>{st.session_state.username or "Unknown"}</b></div>
        <div class="pill">Role: <b>{st.session_state.role or "N/A"}</b></div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="sectionbanner">
      <strong>Overview</strong>
      <div class="pillrow">
        <div class="pill">Total datasets: <b>{len(datasets)}</b></div>
        <div class="pill">Filtered: <b>{len(filtered)}</b></div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Panel toggles (CRUD / AI / Charts)
col_crud, col_ai, col_charts = st.columns(3)

with col_crud:
    if st.button("Dataset CRUD", key="btn_ds_crud"):
        st.session_state.show_dataset_crud = not st.session_state.show_dataset_crud
        if st.session_state.show_dataset_crud:
            st.session_state.assistant_panel_open = False
            st.session_state.show_chart_picker = False

with col_ai:
    if st.button("Data Science AI", key="btn_ds_ai"):
        st.session_state.assistant_panel_open = not st.session_state.assistant_panel_open
        if st.session_state.assistant_panel_open:
            st.session_state.show_dataset_crud = False
            st.session_state.show_chart_picker = False

with col_charts:
    if st.button("Charts", key="btn_ds_charts"):
        st.session_state.show_chart_picker = not st.session_state.show_chart_picker
        if st.session_state.show_chart_picker:
            st.session_state.show_dataset_crud = False
            st.session_state.assistant_panel_open = False

st.info("Note: Only one panel can be active at a time to avoid spoiling the structure and having to scroll completely down.")

if st.session_state.show_chart_picker:
    st.segmented_control(
        "Chart type",
        ["Datasets by Source (Doughnut)", "Category (Radar)"],
        key="selected_chart",
    )

choice = st.session_state.get("selected_chart", "Datasets by Source (Doughnut)")
st.session_state["ds_ai_context"] = build_dataset_context(datasets, filtered, choice)

if st.session_state.show_chart_picker:
    if choice == "Datasets by Source (Doughnut)":
        if not filtered.empty and "source" in filtered.columns:
            src = filtered["source"].value_counts().reset_index()
            src.columns = ["Source", "Count"]
            st.plotly_chart(px.pie(src, names="Source", values="Count", hole=0.4), use_container_width=True)
        else:
            st.info("No source data available to plot.")

    elif choice == "Category (Radar)":
        if not filtered.empty and {"category", "record_count"} <= set(filtered.columns):
            radar = (
                filtered.groupby("category", as_index=False)["record_count"]
                .sum()
                .sort_values("record_count", ascending=False)
            )
            fig = px.line_polar(radar, r="record_count", theta="category", line_close=True)
            fig.update_traces(fill="toself")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("This chart needs both 'category' and 'record_count' columns.")
else:
    st.caption("Charts are hidden. Click Charts to view them.")

if st.session_state.assistant_panel_open:
    st.info("Note: The latest prompt and response appear at the bottom of the chat. Scroll down to view the most recent messages.")

DataScienceChat().render(visible=st.session_state.assistant_panel_open)

if st.session_state.show_dataset_crud:
    DatasetOptions(repo, datasets).render(
        mode=st.session_state.active_dataset_form,
        on_mode_change=lambda m: st.session_state.update(active_dataset_form=m),
    )

st.markdown('<div class="sectionbanner"><strong>Datasets Table</strong></div>', unsafe_allow_html=True)
st.caption(f"Showing **{len(filtered)}** of {len(datasets)} total datasets.")
st.dataframe(filtered, use_container_width=True)

st.divider()

# Log out cleanly and return to Home
if st.button("Log out", key="btn_logout"):
    st.session_state.clear()
    st.switch_page("Home.py")
