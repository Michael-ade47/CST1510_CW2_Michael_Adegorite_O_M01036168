import streamlit as st
import pandas as pd
import numpy as np

from app.data.db import connect_database

# Import Week 8 CRUD functions for each domain
from app.data.users import verify_user, get_user_role

from app.data.incidents import (
    get_all_incidents,
    insert_incident,
    update_incident,
    delete_incident,
)

from app.data.datasets import get_all_datasets

from app.data.tickets import get_all_tickets


st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

# Ensure state keys exist (in case user opens this page first)-
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# Guard: if not logged in, send user back
if not st.session_state.logged_in:
    st.error("You must be logged in to view the dashboard.")
    if st.button("Go to login page"):
        st.switch_page("Home.py")   # back to the first page
    st.stop()

# If logged in, show dashboard content
st.title("📊 Dashboard")
st.success(f"Hello, **{st.session_state.username}**! You are logged in.")

# Example dashboard layout
st.caption("This is just demo content – replace with your own dashboard.")

# Sidebar filters
with st.sidebar:
    st.header("Filters")
    n_points = st.slider("Number of data points", 10, 200, 50)

# Fake data
data = pd.DataFrame(
    np.random.randn(n_points, 3),
    columns=["A", "B", "C"]
)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Line chart")
    st.line_chart(data)

with col2:
    st.subheader("Bar chart")
    st.bar_chart(data)

with st.expander("See raw data"):
    st.dataframe(data)

# Logout button
st.divider()
if st.button("Log out"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.info("You have been logged out.")
    st.switch_page("Home.py")

if not st.session_state.logged_in:
    st.error("You must be logged in...")
    st.switch_page("Home.py")
    st.stop()
