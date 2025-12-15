import sys
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px

# Find the project root
ROOT = Path(__file__).resolve().parents[1]
# Make local imports work
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.database_manager import DatabaseManager
from models.security_incident import (
    IncidentRepository,
    StateManager,
    AuthGuard,
    FilterPanel,
    IncidentFilter,
    CyberChat,
    build_cyber_context,
)

# Page title + layout
st.set_page_config(page_title="Cyber Incidents Dashboard", page_icon="📊", layout="wide")

# Reusable CSS for banners and pills
st.markdown(
    """
    <style>
      .banner {
        padding: 14px 16px;
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,.10);
        background: linear-gradient(135deg, rgba(244,63,94,.14), rgba(59,130,246,.12));
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

# Create session defaults once
StateManager(
    {
        "logged_in": False,          # login flag
        "username": "",              # current user
        "role": "",                  # current role
        "show_incident_crud": False, # CRUD panel
        "active_incident_form": "view",
        "assistant_panel_open": False, # AI panel
        "show_chart_picker": False,    # charts panel
        "selected_chart": "Severity (Bar)",
    }
).init()

# Keep a safe default chart
st.session_state.setdefault("selected_chart", "Severity (Bar)")

# Block access if not logged in
AuthGuard.require_login(login_page="Home.py")

# Open the DB
db = DatabaseManager(str(ROOT / "database" / "platform.db"))
# Use repo for incident ops
repo = IncidentRepository(db)

# Load incidents into a DataFrame
incidents_df = repo.fetch_all_df()
# Stop if there's nothing to show
if incidents_df is None or incidents_df.empty:
    st.info("No incident data available.")
    st.stop()

# Render filter widgets
sev, status = FilterPanel().render_basic()
# Apply filters to the table view
filtered = IncidentFilter.apply_basic(incidents_df, sev, status)

# Explain where filter effects show
st.info(
    "Filters are applied directly to the incidents table. "
    "To see how filtering affects visualisations, open the Charts panel."
)

# Explain where CRUD changes show
st.info(
    "Any changes made using the incident CRUD forms "
    "are reflected immediately in the incidents table below."
)

# Page banner + user identity
st.markdown(
    f"""
    <div class="banner">
      <h2>Cyber Incidents Dashboard</h2>
      <p>Manage and analyse cyber incidents from your multi-domain intelligence platform.</p>
      <div class="pillrow">
        <div class="pill">User: <b>{st.session_state.username or "Unknown"}</b></div>
        <div class="pill">Role: <b>{st.session_state.role or "N/A"}</b></div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Three top buttons (only one panel at a time)
col_crud, col_ai, col_charts = st.columns(3)

with col_crud:
    # Toggle CRUD panel
    if st.button("Incident CRUD", key="btn_toggle_crud"):
        st.session_state.show_incident_crud = not st.session_state.show_incident_crud
        # Close the others
        if st.session_state.show_incident_crud:
            st.session_state.assistant_panel_open = False
            st.session_state.show_chart_picker = False

with col_ai:
    # Toggle AI chat
    if st.button("Cyber AI", key="btn_toggle_ai"):
        st.session_state.assistant_panel_open = not st.session_state.assistant_panel_open
        # Close the others
        if st.session_state.assistant_panel_open:
            st.session_state.show_incident_crud = False
            st.session_state.show_chart_picker = False

with col_charts:
    # Toggle charts panel
    if st.button("Charts", key="btn_charts"):
        st.session_state.show_chart_picker = not st.session_state.show_chart_picker
        # Close the others
        if st.session_state.show_chart_picker:
            st.session_state.show_incident_crud = False
            st.session_state.assistant_panel_open = False

# Small UX reminder
st.info("Only one panel can be active at a time.")

# Overview stats (match the filtered table)
st.markdown(
    f"""
    <div class="sectionbanner">
      <strong>Overview</strong>
      <div class="pillrow">
        <div class="pill">Total (filtered): <b>{len(filtered)}</b></div>
        <div class="pill">High/Critical: <b>{filtered[filtered["severity"].isin(["High", "Critical"])].shape[0] if "severity" in filtered.columns else 0}</b></div>
        <div class="pill">Open/In Progress: <b>{filtered[filtered["status"].isin(["Open", "In Progress"])].shape[0] if "status" in filtered.columns else 0}</b></div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Show chart picker only when open
if st.session_state.show_chart_picker:
    st.segmented_control(
        "Chart type",
        ["Severity (Bar)", "Status (Doughnut)", "Incidents Over Time (Line)"],
        key="selected_chart",
    )

# Current chart selection
choice = st.session_state.get("selected_chart", "Severity (Bar)")

# Build AI context from the same view
st.session_state["cyber_ai_context"] = build_cyber_context(
    incidents_df,  # full data
    filtered,      # filtered view
    choice,        # chart choice
)

# Render charts only when visible
if st.session_state.show_chart_picker:
    if choice == "Severity (Bar)":
        # Bar chart by severity
        if not filtered.empty and "severity" in filtered.columns:
            counts = filtered["severity"].value_counts().reset_index()
            counts.columns = ["Severity", "Count"]
            fig = px.bar(counts, x="Severity", y="Count", text="Count", color="Severity")
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No severity data available to plot.")

    elif choice == "Status (Doughnut)":
        # Doughnut chart by status
        if not filtered.empty and "status" in filtered.columns:
            sc = filtered["status"].value_counts().reset_index()
            sc.columns = ["Status", "Count"]
            fig = px.pie(sc, names="Status", values="Count", hole=0.45)
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No status data available to plot.")

    elif choice == "Incidents Over Time (Line)":
        # Line chart by date
        if not filtered.empty and "date" in filtered.columns:
            tmp = filtered.copy()
            tmp["date"] = pd.to_datetime(tmp["date"], errors="coerce")
            tmp = tmp.dropna(subset=["date"])
            # Stop if dates are messy
            if tmp.empty:
                st.info("Date column exists, but no valid dates to plot.")
            else:
                daily = tmp.groupby(tmp["date"].dt.date).size().reset_index(name="Count")
                daily.columns = ["Date", "Count"]
                fig = px.line(daily, x="Date", y="Count", markers=True)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("This chart needs a 'date' column in your incidents table.")
else:
    # Keep the page clear when closed
    st.caption("Charts are hidden. Click Charts to view them.")

# Help users find the newest AI reply
if st.session_state.assistant_panel_open:
    st.info("Latest chat messages appear at the bottom.")

# Render chat (hidden unless enabled)
CyberChat().render(visible=st.session_state.assistant_panel_open)

# Main table section
st.markdown('<div class="sectionbanner"><strong>All Incidents (Filtered)</strong></div>', unsafe_allow_html=True)
st.dataframe(filtered, use_container_width=True)

st.divider()

# Logout and reset session
if st.button("Log out", key="btn_logout"):
    st.session_state.clear()
    st.switch_page("Home.py")
