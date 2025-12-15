import sys
from pathlib import Path
from datetime import date

import streamlit as st
import pandas as pd
import plotly.express as px

# Find the project root so local imports work in Streamlit
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.database_manager import DatabaseManager
from models.it_ticket import (
    StateManager,
    AuthGuard,
    ITTicketRepository,
    TicketFilterPanel,
    TicketFilter,
    ITSupportChat,
    TicketCRUD,
    build_it_context,
)

# Page identity + layout
st.set_page_config(page_title="IT Tickets", page_icon="💻", layout="wide")

# Small CSS bundle to keep the page styling consistent
st.markdown(
    """
    <style>
      .banner {
        padding: 14px 16px;
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,.10);
        background: linear-gradient(135deg, rgba(59,130,246,.18), rgba(16,185,129,.10));
        margin: 8px 0 14px 0;
      }
      .pillrow {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin-top: 10px;
      }
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
    </style>
    """,
    unsafe_allow_html=True,
)

# Set up session defaults so reruns don't break UI state
StateManager(
    {
        "logged_in": False,
        "username": "",
        "role": "",
        "assistant_panel_open": False,
        "show_ticket_crud": False,
        "active_ticket_form": None,
        "show_chart_picker": False,
        "show_table_picker": False,
    }
).init()

# Default selections for charts/tables
st.session_state.setdefault("selected_chart", "Status (Doughnut)")
st.session_state.setdefault("selected_table", "All Tickets")

# Require login before showing ticket data
AuthGuard.require_login(login_page="Home.py")

# Open DB and repository for ticket operations
db = DatabaseManager(str(ROOT / "database" / "platform.db"))
repo = ITTicketRepository(db)

# Load tickets into a DataFrame for filtering and plotting
tickets = repo.read_all_df()
if tickets.empty:
    st.info("No IT tickets found.")
    st.stop()

# Render filter widgets and apply them to the table view
status_f, priority_f, assignee_f, min_age = TicketFilterPanel().render(tickets)
filtered = TicketFilter.apply(tickets, status_f, priority_f, assignee_f, min_age)

# Explain where filter/CRUD effects will show up
st.info(
    "Filter effects are applied to the tables automatically. "
    "To see how filters affect visualisations, open the Charts panel."
)
st.info(
    "Any changes made using the CRUD forms (create, update, delete) "
    "are reflected immediately in the table below."
)

# Build the AI context from the same view the user is working with
st.session_state["it_ai_context"] = build_it_context(tickets, filtered)

# Page banner
st.markdown(
    f"""
    <div class="banner">
      <h2>IT Operations</h2>
      <p>Track, filter, and resolve IT support tickets.</p>
      <div class="pillrow">
        <div class="pill">User: <b>{st.session_state.username}</b></div>
        <div class="pill">Role: <b>{st.session_state.role}</b></div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Quick overview stats (match the filtered table)
st.markdown(
    f"""
    <div class="sectionbanner">
      <strong>Overview</strong>
      <div class="pillrow">
        <div class="pill">Total: <b>{len(tickets)}</b></div>
        <div class="pill">Filtered: <b>{len(filtered)}</b></div>
        <div class="pill">Open/In Progress: <b>{filtered[filtered["status"].isin(["Open","In Progress"])].shape[0] if "status" in filtered.columns else 0}</b></div>
        <div class="pill">High/Critical: <b>{filtered[filtered["priority"].isin(["High","Critical"])].shape[0] if "priority" in filtered.columns else 0}</b></div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Top buttons (CRUD / AI / Charts)
col_crud, col_ai, col_charts = st.columns(3)

with col_crud:
    # Toggle CRUD panel and close the others
    if st.button("Ticket CRUD", key="btn_ticket_crud"):
        st.session_state.show_ticket_crud = not st.session_state.show_ticket_crud
        if st.session_state.show_ticket_crud:
            st.session_state.assistant_panel_open = False
            st.session_state.show_chart_picker = False

with col_ai:
    # Toggle AI chat and close the others
    if st.button("IT AI", key="btn_it_ai"):
        st.session_state.assistant_panel_open = not st.session_state.assistant_panel_open
        if st.session_state.assistant_panel_open:
            st.session_state.show_ticket_crud = False
            st.session_state.show_chart_picker = False

with col_charts:
    # Toggle charts panel and close the others
    if st.button("Charts", key="btn_charts"):
        st.session_state.show_chart_picker = not st.session_state.show_chart_picker
        if st.session_state.show_chart_picker:
            st.session_state.show_ticket_crud = False
            st.session_state.assistant_panel_open = False

# Small reminder so users know why panels collapse
st.info("Note: Only one panel can be active at a time to avoid spoiling the structure and having to scroll completely down.")

# Charts panel
if st.session_state.show_chart_picker:
    # Pick which chart to show
    st.segmented_control(
        "Chart type",
        ["Status (Doughnut)", "Priority (Radar)", "Delays by Employee"],
        key="selected_chart",
    )

    # Read current choice from session state
    choice = st.session_state.get("selected_chart", "Status (Doughnut)")

    # Pull out delayed tickets (open/in progress with a known age)
    delayed = filtered[
        (filtered.get("age_days", pd.Series([None] * len(filtered))).notna())
        & (filtered.get("status", pd.Series([""] * len(filtered))).isin(["Open", "In Progress"]))
    ].copy()

    # Summarise delays per assignee (useful for workload bottlenecks)
    blockers = (
        delayed.groupby("assigned_to", as_index=False)
        .agg(
            delayed_tickets=("ticket_id", "count") if "ticket_id" in delayed.columns else ("age_days", "count"),
            total_days_open=("age_days", "sum"),
            avg_days_open=("age_days", "mean"),
        )
        .sort_values("total_days_open", ascending=False)
        if "assigned_to" in delayed.columns and not delayed.empty
        else pd.DataFrame()
    )

    if choice == "Status (Doughnut)":
        # Distribution of ticket statuses
        if "status" in filtered.columns and not filtered.empty:
            sc = filtered["status"].value_counts().reset_index()
            sc.columns = ["status", "count"]
            fig = px.pie(sc, names="status", values="count", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No status data available to plot.")

    elif choice == "Priority (Radar)":
        # Priorities as a quick “pressure gauge”
        if "priority" in filtered.columns and not filtered.empty:
            pc = filtered["priority"].value_counts().reset_index()
            pc.columns = ["priority", "count"]
            fig = px.bar_polar(pc, r="count", theta="priority")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No priority data available to plot.")

    elif choice == "Delays by Employee":
        # Who has the biggest delay backlog
        if not blockers.empty:
            fig = px.bar(
                blockers.head(10),
                x="total_days_open",
                y="assigned_to",
                orientation="h",
                color="delayed_tickets",
                color_continuous_scale="Turbo",
                text="total_days_open",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(coloraxis_colorbar=dict(title="Delayed Tickets"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No delay/assignee data available to plot.")
else:
    # Keep the UI tidy when charts are closed
    st.caption("Charts are hidden. Click Charts to view them.")

# Helpful hint for chat scrolling
if st.session_state.assistant_panel_open:
    st.info("Note: The latest prompt and response appear at the bottom of the chat. Scroll down to view the most recent messages.")

# Render the AI chat panel
ITSupportChat().render(visible=st.session_state.assistant_panel_open)

# Render CRUD panel (create/update/delete)
TicketCRUD(repo, tickets).render(visible=st.session_state.show_ticket_crud)

# Tables controls: button + picker
col_tables_btn, col_tables_pick = st.columns([1, 3])

with col_tables_btn:
    # Toggle table selector
    if st.button("Tables", key="btn_tables"):
        st.session_state.show_table_picker = not st.session_state.show_table_picker

with col_tables_pick:
    # Let the user pick which table view they want
    if st.session_state.show_table_picker:
        st.segmented_control(
            "Table type",
            ["All Tickets", "Top 10 Greatest Delays"],
            key="selected_table",
        )

# Read which table is selected
table_choice = st.session_state.get("selected_table", "All Tickets")

if table_choice == "Top 10 Greatest Delays":
    # Focused view: longest-open active tickets
    st.markdown(
        '<div class="sectionbanner"><strong>Top 10 Tickets With Greatest Delay</strong></div>',
        unsafe_allow_html=True,
    )
    # Needs age + status to rank delays properly
    if "age_days" in filtered.columns and "status" in filtered.columns:
        top10 = (
            filtered[filtered["status"].isin(["Open", "In Progress"])]
            .dropna(subset=["age_days"])
            .sort_values("age_days", ascending=False)
            .head(10)
        )
        # Prefer a clean column set, but fall back if schema differs
        preferred_cols = [
            "ticket_id",
            "status",
            "priority",
            "category",
            "subject",
            "assigned_to",
            "age_days",
            "created_at",
            "created_on",
            "created_date",
        ]
        cols = [c for c in preferred_cols if c in top10.columns]
        st.dataframe(top10[cols] if cols else top10, use_container_width=True)
    else:
        st.info("This table needs both 'age_days' and 'status' columns to be present.")
else:
    # Default view: the filtered tickets table
    st.markdown('<div class="sectionbanner"><strong>Tickets Table</strong></div>', unsafe_allow_html=True)
    st.dataframe(filtered, use_container_width=True)

st.divider()

# Log out and reset session state
if st.button("Log out", key="btn_logout"):
    st.session_state.clear()
    st.switch_page("Home.py")
