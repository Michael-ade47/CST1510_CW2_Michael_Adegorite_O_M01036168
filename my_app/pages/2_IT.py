import sys
from pathlib import Path
from datetime import datetime, date

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
import plotly.express as px

from app.data.db import connect_database  
from app.data.users import verify_user, get_user_role  
from app.data.tickets import get_all_tickets, insert_ticket
from app.data.tickets import get_all_tickets, insert_ticket, delete_ticket
from app.data.tickets import (
    get_all_tickets,
    insert_ticket,
    delete_ticket,
    update_ticket_status,
)


st.set_page_config(page_title="IT Tickets", page_icon="💻", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.error("You must be logged in to view this page.")
    if st.button("Go to login page"):
        st.switch_page("Home.py")
    st.stop()

st.title("IT Tickets")
st.success(f"Hello, **{st.session_state.username}**! Here are the IT tickets.")

try:
    it_tickets = get_all_tickets()
except Exception as e:
    st.error(f"Error loading IT tickets: {e}")
    it_tickets = pd.DataFrame()

if it_tickets is None or it_tickets.empty:
    st.info("No IT tickets found in the database.")
    st.stop()

date_column = None
for candidate in ["created_date", "created_at", "created", "date", "opened_at"]:
    if candidate in it_tickets.columns:
        date_column = candidate
        break

if date_column:
    it_tickets[date_column] = pd.to_datetime(it_tickets[date_column], errors="coerce")
    today_ts = pd.Timestamp(date.today())
    it_tickets["age_days"] = (today_ts - it_tickets[date_column]).dt.days
else:
    it_tickets["age_days"] = pd.NA

with st.sidebar:
    st.header("Filters – Delays in Resolution")

    status_options = (
        sorted(it_tickets["status"].dropna().unique())
        if "status" in it_tickets.columns
        else []
    )
    status_filter = st.multiselect("Status", options=status_options)

    priority_options = (
        sorted(it_tickets["priority"].dropna().unique())
        if "priority" in it_tickets.columns
        else []
    )
    priority_filter = st.multiselect("Priority", options=priority_options)

    assignee_filter = []
    if "assigned_to" in it_tickets.columns:
        assignee_options = sorted(it_tickets["assigned_to"].dropna().unique())
        assignee_filter = st.multiselect("Assigned to", options=assignee_options)

    min_age = 0
    if "age_days" in it_tickets.columns and it_tickets["age_days"].notna().any():
        max_age = int(it_tickets["age_days"].max())
        min_age = st.slider(
            "Minimum days open",
            min_value=0,
            max_value=max_age if max_age > 0 else 0,
            value=0,
            help="Show tickets that have been open at least this many days.",
        )

filtered = it_tickets.copy()

for col, values in [
    ("status", status_filter),
    ("priority", priority_filter),
    ("assigned_to", assignee_filter),
]:
    if values and col in filtered.columns:
        filtered = filtered[filtered[col].isin(values)]

if "age_days" in filtered.columns and min_age > 0:
    filtered = filtered[filtered["age_days"] >= min_age]

st.subheader("IT Tickets Table (Filtered)")
st.caption(f"Showing **{len(filtered)}** of {len(it_tickets)} total tickets.")
st.dataframe(filtered, use_container_width=True)

if "age_days" in filtered.columns and filtered["age_days"].notna().any():
    st.subheader("Tickets with Greatest Delays")

    delayed = filtered.copy()
    if "status" in delayed.columns:
        delayed = delayed[delayed["status"].isin(["Open", "In Progress"])]

    if not delayed.empty:
        delayed = delayed.sort_values("age_days", ascending=False)

        st.caption("Oldest open/in-progress tickets (longest time since creation).")
        st.dataframe(delayed.head(10), use_container_width=True)

        if "assigned_to" in delayed.columns:
            st.subheader("Delayed Tickets by Assignee")
            delay_by_assignee = (
                delayed.groupby("assigned_to")["age_days"]
                .mean()
                .reset_index()
                .sort_values("age_days", ascending=False)
            )
            delay_by_assignee = delay_by_assignee.rename(
                columns={"age_days": "Average days open"}
            )

            fig_delay = px.bar(
                delay_by_assignee,
                x="assigned_to",
                y="Average days open",
                title="Delayed Tickets by Assignee",
                text="Average days open",
            )
            fig_delay.update_traces(textposition="outside")
            fig_delay.update_layout(
                xaxis_title="Assignee", yaxis_title="Average days open"
            )
            st.plotly_chart(fig_delay, use_container_width=True)
    else:
        st.info("No delayed open/in-progress tickets based on current filters.")
else:
    st.info("No age information available to analyse ticket delays (no date column found).")

st.subheader("Tickets by Status (Filtered)")
if "status" in filtered.columns:
    status_counts = filtered["status"].value_counts().reset_index()
    status_counts.columns = ["Status", "Count"]

    fig_status = px.bar(
        status_counts,
        x="Status",
        y="Count",
        title="Tickets by Status",
        text="Count",
    )
    fig_status.update_traces(textposition="outside")
    fig_status.update_layout(yaxis_title="Number of tickets")
    st.plotly_chart(fig_status, use_container_width=True)
else:
    st.info("No 'status' column found to show tickets by status.")

st.subheader("Tickets by Priority (Filtered)")
if "priority" in filtered.columns:
    priority_counts = filtered["priority"].value_counts().reset_index()
    priority_counts.columns = ["Priority", "Count"]

    fig_priority = px.bar(
        priority_counts,
        x="Priority",
        y="Count",
        title="Tickets by Priority",
        text="Count",
    )
    fig_priority.update_traces(textposition="outside")
    fig_priority.update_layout(yaxis_title="Number of tickets")
    st.plotly_chart(fig_priority, use_container_width=True)
else:
    st.info("No 'priority' column found to show tickets by priority.")

st.subheader("Create New IT Ticket")

with st.form("new_it_ticket"):
    created_date = st.date_input("Date")
    category = st.text_input("Category")
    subject = st.text_input("Subject / Short title")
    priority = st.selectbox("Priority", ["Low", "Medium", "High", "Critical"])
    status = st.selectbox("Status", ["Open", "In Progress", "Resolved", "Closed"])
    assigned_to = st.text_input("Assigned to (optional)")
    description = st.text_area("Description")

    submit_new_ticket = st.form_submit_button("Create ticket")
    if submit_new_ticket:
        if not category:
            st.error("Please enter a category or short title for the ticket.")
        elif not subject:
            st.error("Please enter a subject for the ticket.")
        else:
            ticket_id = insert_ticket(
                created_date.strftime("%Y-%m-%d"),
                category,
                subject,
                priority,
                status,
                description,
                assigned_to or None,
            )
            st.success(f"IT ticket {ticket_id} created successfully!")
            st.rerun()

st.subheader("Delete a Ticket")

tickets_df = get_all_tickets()

if tickets_df.empty:
    st.info("No tickets available to delete.")
else:
    ticket_options = tickets_df.apply(
        lambda row: f"{row['id']} | {row['ticket_id']} | {row['subject']}",
        axis=1,
    )

    selected_ticket = st.selectbox("Select a ticket to delete:", ticket_options)

    selected_id_str = selected_ticket.split("|")[0].strip()
    selected_ticket_id = int(selected_id_str)

    confirm_delete = st.checkbox("Yes, I would like to delete this ticket.")

    if st.button("Delete Ticket"):
        if not confirm_delete:
            st.warning("Please confirm before deleting.")
        else:
            deleted = delete_ticket(selected_ticket_id)
            if deleted == 0:
                st.error("No ticket was deleted. Check that the ID is correct.")
            else:
                st.success(f"Ticket ID {selected_ticket_id} deleted successfully!")
                st.rerun()
st.subheader("Update Ticket Status")

tickets_df = get_all_tickets()

if tickets_df.empty:
    st.info("No tickets available to update.")
else:
    update_options = tickets_df.apply(
        lambda row: f"{row['ticket_id']} | {row['subject']} | {row['status']}",
        axis=1,
    )

    selected_update = st.selectbox(
        "Select a ticket to update:",
        update_options,
        key="update_ticket_select",
    )

    selected_ticket_id = selected_update.split("|")[0].strip()

    current_status = tickets_df.loc[
        tickets_df["ticket_id"] == selected_ticket_id, "status"
    ].iloc[0]

    status_choices = ["Open", "In Progress", "Resolved", "Closed"]

    default_index = status_choices.index(current_status) if current_status in status_choices else 0

    with st.form("update_ticket_status_form"):
        new_status = st.selectbox(
            "New status",
            options=status_choices,
            index=default_index,
        )

        submit_update = st.form_submit_button("Update status")

    if submit_update:
        if new_status == current_status:
            st.info("Status is already set to this value.")
        else:
            update_ticket_status(selected_ticket_id, new_status)
            st.success(
                f"Status for ticket **{selected_ticket_id}** has been updated "
                f"from **{current_status}** to **{new_status}**."
            )
            st.rerun()
st.subheader("Read Tickets Record")

tickets_df = get_all_tickets()

if tickets_df.empty:
    st.info("No tickets available to read.")
else:
    
    read_options = tickets_df.apply(
        lambda row: f"{row['ticket_id']} | {row['subject']}",
        axis=1,
    )

    selected_read = st.selectbox(
        "Select a ticket to read:",
        read_options,
        key="read_ticket_select",   
    )

    selected_ticket_id = selected_read.split("|")[0].strip()

    selected_ticket = tickets_df[
        tickets_df["ticket_id"] == selected_ticket_id
    ].iloc[0]

    st.markdown("### Ticket Details")

    col1, col2 = st.columns(2)

    with col1:
        st.text_input("Ticket ID", value=selected_ticket["ticket_id"], disabled=True)
        st.text_input("Category", value=selected_ticket["category"], disabled=True)
        st.text_input("Priority", value=selected_ticket["priority"], disabled=True)
        st.text_input("Status", value=selected_ticket["status"], disabled=True)

    with col2:
        st.text_input("Created Date", value=str(selected_ticket["created_date"]), disabled=True)
        st.text_input("Assigned To", value=str(selected_ticket["assigned_to"]), disabled=True)
        st.text_input("Subject", value=selected_ticket["subject"], disabled=True)

    st.text_area(
        "Description",
        value=selected_ticket["description"],
        disabled=True,
        height=120,
    )



st.divider()
if st.button("Log out"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.info("You have been logged out.")
    st.switch_page("Home.py")
