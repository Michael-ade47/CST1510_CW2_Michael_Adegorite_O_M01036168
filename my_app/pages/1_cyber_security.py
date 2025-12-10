import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[2]

load_dotenv(ROOT / ".env")

api_key = os.getenv("OPENAI_API_KEY")

if api_key:
    print("OPENAI_API_KEY loaded (last 6):", api_key[-6:])
else:
    print("OPENAI_API_KEY NOT loaded")

client = OpenAI(api_key=api_key) if api_key else None

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
import plotly.express as px

from app.data.db import connect_database
from app.data.users import verify_user, get_user_role
from app.data.incidents import (
    get_all_incidents,
    insert_incident,
    update_incident_status,
    delete_incident,
)


st.set_page_config(page_title="Cyber Incidents Dashboard", page_icon="📊", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.error("You must be logged in to view the dashboard.")
    if st.button("Go to login page"):
        st.switch_page("Home.py")
    st.stop()

st.title("Cyber Incidents Dashboard")
st.success(f"Hello, **{st.session_state.username}**! You are logged in.")
st.caption("Manage and analyse cyber incidents, datasets, and IT tickets from your dashboard.")
if "active_incident_form" not in st.session_state:
    st.session_state.active_incident_form = None

with st.sidebar:
    st.header("Filters")

    severity_filter = st.multiselect(
        "Severity",
        options=["Low", "Medium", "High", "Critical"],
    )

    status_filter = st.multiselect(
        "Status",
        options=["Open", "In Progress", "Resolved"],
    )

    date_range = st.date_input(
        "Date range",
        value=[],
        help="Filter incidents between two dates (inclusive).",
    )


    search_text = st.text_input(
        "Search (type/description/reported by)",
        placeholder="e.g. phishing, malware, user123…",
    )

    st.markdown("---")
    st.caption("Use the filters above to refine the incidents shown on the dashboard.")
    if "active_incident_form" not in st.session_state:
        st.session_state.active_incident_form = None

if "show_incident_crud" not in st.session_state:
    st.session_state.show_incident_crud = False


incidents = get_all_incidents()

if incidents is None or incidents.empty:
    st.info("No incident data available.")
    st.stop()

filtered_incidents = incidents.copy()

if "date" in filtered_incidents.columns:
    filtered_incidents["date"] = pd.to_datetime(
        filtered_incidents["date"], errors="coerce"
    )

if severity_filter and "severity" in filtered_incidents.columns:
    filtered_incidents = filtered_incidents[
        filtered_incidents["severity"].isin(severity_filter)
    ]

if status_filter and "status" in filtered_incidents.columns:
    filtered_incidents = filtered_incidents[
        filtered_incidents["status"].isin(status_filter)
    ]

if (
    "date" in filtered_incidents.columns
    and len(date_range) == 2
    and all(date_range)
):
    start_date, end_date = date_range
    filtered_incidents = filtered_incidents[
        (filtered_incidents["date"].dt.date >= start_date)
        & (filtered_incidents["date"].dt.date <= end_date)
    ]

if search_text:
    search_lower = search_text.lower()

    searchable_cols = [
        col for col in ["incident_type", "description", "reported_by", "title"]
        if col in filtered_incidents.columns
    ]

    if searchable_cols:
        search_mask = filtered_incidents[searchable_cols].astype(str).apply(
            lambda row: row.str.lower().str.contains(search_lower, na=False).any(),
            axis=1,
        )
        filtered_incidents = filtered_incidents[search_mask]

st.subheader("Security Overview")
col1, col2, col3 = st.columns(3)

total_incidents = len(filtered_incidents)
high_crit_incidents = 0
if "severity" in filtered_incidents.columns:
    high_crit_incidents = filtered_incidents[
        filtered_incidents["severity"].isin(["High", "Critical"])
    ].shape[0]

open_incidents = 0
if "status" in filtered_incidents.columns:
    open_incidents = filtered_incidents[
        filtered_incidents["status"].isin(["Open", "In Progress"])
    ].shape[0]

with col1:
    st.metric("Total Incidents (filtered)", total_incidents)
with col2:
    st.metric("High/Critical Incidents", high_crit_incidents)
with col3:
    st.metric("Open / In Progress", open_incidents)

st.subheader("All Incidents (Filtered)")
st.dataframe(filtered_incidents, use_container_width=True)

if not filtered_incidents.empty:
    if "severity" in filtered_incidents.columns:
        st.subheader("Incidents by Severity")

        severity_counts = (
            filtered_incidents["severity"]
            .value_counts()
            .reset_index()
        )
        severity_counts.columns = ["Severity", "Count"]

        fig_severity = px.bar(
            severity_counts,
            x="Severity",
            y="Count",
            title="Incidents by Severity",
            text="Count",
        )
        fig_severity.update_traces(textposition="outside")
        fig_severity.update_layout(yaxis_title="Number of Incidents")
        st.plotly_chart(fig_severity, use_container_width=True)
    else:
        st.info("No 'severity' column found in incidents data.")

    if "date" in filtered_incidents.columns:
        st.subheader("Incidents Over Time")

        view_choice = st.radio(
            "Time aggregation",
            ["Daily", "Monthly"],
            horizontal=True,
        )

        base = filtered_incidents.dropna(subset=["date"]).copy()

        if base.empty:
            st.info("No valid dates available to plot incident trends.")
        else:
            if view_choice == "Daily":
                daily_counts = (
                    base
                    .groupby(base["date"].dt.date)
                    .size()
                    .reset_index(name="Count")
                )
                daily_counts = daily_counts.rename(columns={"date": "Date"})

                fig_time = px.line(
                    daily_counts,
                    x="Date",
                    y="Count",
                    markers=True,
                    title="Incidents per Day",
                )
                fig_time.update_layout(yaxis_title="Number of Incidents")
                st.plotly_chart(fig_time, use_container_width=True)

            else:  
                monthly_counts = (
                    base
                    .groupby(base["date"].dt.to_period("M"))
                    .size()
                    .reset_index(name="Count")
                )

                monthly_counts["Month"] = monthly_counts["date"].dt.to_timestamp()

                fig_monthly = px.line(
                    monthly_counts,
                    x="Month",
                    y="Count",
                    markers=True,
                    title="Incidents per Month",
                )
                fig_monthly.update_layout(yaxis_title="Number of Incidents")
                st.plotly_chart(fig_monthly, use_container_width=True)
    else:
        st.info("No 'date' column found to show incident timeline.")
else:
    st.info("No incidents match the current filter selection.")



st.subheader("Incident Actions")

if st.button(" Show / Hide Incident CRUD Tools"):
    st.session_state.show_incident_crud = not st.session_state.show_incident_crud
    if not st.session_state.show_incident_crud:
        st.session_state.active_incident_form = None

if st.session_state.show_incident_crud:
    crud_choice = st.radio(
        "Choose what you want to do:",
        options=[
            "Create incident",
            "Read incident details",
            "Update incident status",
            "Delete incident",
        ],
        horizontal=True,
    )

    mapping = {
        "Create incident": "create",
        "Read incident details": "view",
        "Update incident status": "update",
        "Delete incident": "delete",
    }
    st.session_state.active_incident_form = mapping[crud_choice]

st.markdown("---")


if st.session_state.active_incident_form == "create":
    st.subheader("Create New Incident")

    with st.form("new_incident"):
        date_input = st.date_input("Date")
        incident_type = st.text_input("Incident Type / Title")
        severity = st.selectbox("Severity", ["Low", "Medium", "High", "Critical"])
        status = st.selectbox("Status", ["Open", "In Progress", "Resolved"])
        description = st.text_area("Description")

        submitted_incident = st.form_submit_button("Add Incident")

        if submitted_incident:
            if not incident_type:
                st.error("Please enter a type/title for the incident.")
            else:
                incident_id = insert_incident(
                    date_input.strftime("%Y-%m-%d"),
                    incident_type,
                    severity,
                    status,
                    description,
                    reported_by=st.session_state.username or "dashboard_user",
                )
                st.success(f"Incident #{incident_id} added successfully!")
                st.rerun()

elif st.session_state.active_incident_form == "delete":
    st.subheader("Delete Incident")

    if filtered_incidents.empty or "id" not in filtered_incidents.columns:
        st.info("No incidents available to delete.")
    else:
        options = []
        for _, row in filtered_incidents.iterrows():
            inc_id = row["id"]
            inc_type = row.get("incident_type", "N/A")
            inc_sev = row.get("severity", "Unknown")
            inc_status = row.get("status", "Unknown")
            label = f"#{inc_id} – {inc_type} [{inc_sev}, {inc_status}]"
            options.append((inc_id, label))

        id_list = [item[0] for item in options]
        label_map = {item[0]: item[1] for item in options}

        with st.form("delete_incident_form"):
            selected_id = st.selectbox(
                "Select incident to delete",
                options=id_list,
                format_func=lambda x: label_map.get(x, str(x)),
            )

            confirm = st.checkbox(
                "I understand this will permanently delete the selected incident."
            )

            submitted_delete = st.form_submit_button("Delete incident")

            if submitted_delete:
                if not confirm:
                    st.warning("Please tick the confirmation box before deleting.")
                else:
                    delete_incident(selected_id)
                    st.success(f"Incident #{selected_id} deleted successfully.")
                    st.rerun()

elif st.session_state.active_incident_form == "update":
    st.subheader("Update Incident Status")

    if filtered_incidents.empty or "id" not in filtered_incidents.columns:
        st.info("No incidents available to update.")
    else:
        options = []
        for _, row in filtered_incidents.iterrows():
            inc_id = row["id"]
            inc_type = row.get("incident_type", "N/A")
            inc_status = row.get("status", "Unknown")
            label = f"#{inc_id} – {inc_type} [{inc_status}]"
            options.append((inc_id, label))

        id_list = [item[0] for item in options]
        label_map = {item[0]: item[1] for item in options}

        with st.form("update_incident_form"):
            selected_id = st.selectbox(
                "Select incident to update",
                options=id_list,
                format_func=lambda x: label_map.get(x, str(x)),
            )

            if "status" in filtered_incidents.columns:
                current_status = (
                    filtered_incidents.loc[
                        filtered_incidents["id"] == selected_id, "status"
                    ]
                    .iloc[0]
                )
            else:
                current_status = "Open"

            status_options = ["Open", "In Progress", "Resolved"]
            if current_status in status_options:
                default_index = status_options.index(current_status)
            else:
                default_index = 0

            new_status = st.selectbox(
                "New status",
                status_options,
                index=default_index,
            )

            submitted_update = st.form_submit_button("Update incident")

            if submitted_update:
                update_incident_status(selected_id, new_status)
                st.success(f"Incident #{selected_id} status updated to **{new_status}**.")
                st.rerun()

elif st.session_state.active_incident_form == "view":
    st.subheader("Read Incident Details")

    if filtered_incidents.empty or "id" not in filtered_incidents.columns:
        st.info("No incidents available to view.")
    else:
        options = []
        for _, row in filtered_incidents.iterrows():
            inc_id = row["id"]
            inc_type = row.get("incident_type", "N/A")
            inc_sev = row.get("severity", "Unknown")
            inc_status = row.get("status", "Unknown")
            label = f"#{inc_id} – {inc_type} [{inc_sev}, {inc_status}]"
            options.append((inc_id, label))

        id_list = [item[0] for item in options]
        label_map = {item[0]: item[1] for item in options}

        with st.form("view_incident_form"):
            selected_id = st.selectbox(
                "Select incident to view",
                options=id_list,
                format_func=lambda x: label_map.get(x, str(x)),
            )

            submitted_view = st.form_submit_button("Show details")

            if submitted_view:
                row = filtered_incidents.loc[
                    filtered_incidents["id"] == selected_id
                ].iloc[0]

                st.markdown(f"### Incident #{selected_id}")
                st.write(f"**Type / Title:** {row.get('incident_type', 'N/A')}")
                st.write(f"**Severity:** {row.get('severity', 'N/A')}")
                st.write(f"**Status:** {row.get('status', 'N/A')}")
                st.write(f"**Date:** {row.get('date', 'N/A')}")
                st.write(f"**Reported by:** {row.get('reported_by', 'N/A')}")
                st.write("**Description:**")
                st.write(row.get("description", "N/A"))


st.subheader("AI Assistant")

if "assistant_panel_open" not in st.session_state:
    st.session_state.assistant_panel_open = False

if "assistant_mode" not in st.session_state:
    st.session_state.assistant_mode = "cyber"  

if st.button(" Show / Hide AI Assistant Panel"):
    st.session_state.assistant_panel_open = not st.session_state.assistant_panel_open

if not st.session_state.assistant_panel_open:
    st.stop()

mode = st.radio(
    "Choose which assistant you want to use:",
    options=["Cyber Security", "IT Support", "Data Science"],
    horizontal=True,
)

if mode == "Cyber Security":
    st.session_state.assistant_mode = "cyber"
elif mode == "IT Support":
    st.session_state.assistant_mode = "it"
else:
    st.session_state.assistant_mode = "ds"

mode = st.session_state.assistant_mode

if mode == "cyber":
    chat_key = "cyber_chat"
    title = "Cyber Security AI Assistant "
    placeholder = "Ask the Cyber Security Assistant about incidents, threats, or security concepts…"
    spinner_text = "Thinking like a cyber security expert..."
    system_prompt = (
        "You are a cyber security expert. "
        "You explain cyber security concepts clearly, provide practical examples, "
        "and follow best security practices. "
        "When relevant, relate your answers to incident response, SIEM, and threat detection."
    )
elif mode == "it":
    chat_key = "it_chat"
    title = "IT (Information Technology) AI Assistant "
    placeholder = "Ask the IT Assistant about tickets, troubleshooting, or IT issues…"
    spinner_text = "Thinking like an IT specialist..."
    system_prompt = (
        "You are an Information Technology (IT) expert. "
        "You explain IT concepts clearly and practically, including networking, "
        "operating systems, hardware, software, databases, and cloud computing. "
        "You provide step-by-step troubleshooting guidance and follow industry best practices. "
        "When relevant, relate your answers to system administration, IT support, "
        "incident handling, and infrastructure management."
    )
else:  
    chat_key = "ds_chat"
    title = "Data Science AI Assistant "
    placeholder = "Ask the Data Science Assistant about datasets, analysis, or machine learning…"
    spinner_text = "Thinking like a Data Scientist..."
    system_prompt = (
        "You are a Data Science expert. "
        "You explain data science concepts clearly and practically, including "
        "data cleaning, exploratory data analysis (EDA), data visualization, "
        "machine learning, statistics, feature engineering, and model evaluation. "
        "You provide step-by-step guidance using real-world datasets and best practices. "
        "When relevant, relate your answers to business analytics, predictive modeling, "
        "and data-driven decision making."
    )

st.markdown(f"### {title}")

if client is None:
    st.warning(f"{title} is not available (missing API key).")
else:
    if chat_key not in st.session_state:
        st.session_state[chat_key] = [
            {
                "role": "system",
                "content": system_prompt,
            }
        ]
    else:
        if not st.session_state[chat_key] or st.session_state[chat_key][0]["role"] != "system":
            st.session_state[chat_key].insert(0, {"role": "system", "content": system_prompt})

    for msg in st.session_state[chat_key]:
        if msg["role"] == "system":
            continue
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_prompt = st.chat_input(placeholder)

    if user_prompt:
        st.session_state[chat_key].append({"role": "user", "content": user_prompt})

        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            with st.spinner(spinner_text):
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=st.session_state[chat_key],
                )
                ai_message = response.choices[0].message.content
                st.markdown(ai_message)

        st.session_state[chat_key].append(
            {"role": "assistant", "content": ai_message}
        )

st.divider()
if st.button("Log out"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.info("You have been logged out.")
    st.switch_page("Home.py")
