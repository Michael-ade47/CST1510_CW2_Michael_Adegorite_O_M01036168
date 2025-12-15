import sys
import sqlite3
from pathlib import Path

# Resolve project root so imports work from Streamlit pages
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from services.database_manager import DatabaseManager
from services.auth_manager import AuthManager

# Basic page setup for the auth screen
st.set_page_config(page_title="Login / Register", page_icon="🔐", layout="centered")

# Simple CSS for a clean login/register banner
st.markdown(
    """
    <style>
      .banner {
        padding: 18px 20px;
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,.12);
        background: linear-gradient(135deg, rgba(59,130,246,.20), rgba(16,185,129,.12));
        margin-bottom: 20px;
        text-align: center;
      }
      .banner h2 {
        margin: 0;
        font-size: 24px;
        font-weight: 600;
      }
      .banner p {
        margin-top: 8px;
        opacity: .85;
        font-size: 14px;
      }
      .pillrow {
        display: flex;
        justify-content: center;
        gap: 12px;
        margin-top: 12px;
        flex-wrap: wrap;
      }
      .pill {
        padding: 6px 12px;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,.14);
        background: rgba(255,255,255,.06);
        font-size: 13px;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# Ensure expected session keys exist
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""

# Initialise database and authentication manager
db_path = ROOT / "database" / "platform.db"
db = DatabaseManager(str(db_path))
db.init_schema()  # Make sure tables exist
auth = AuthManager(db)

# Page header shown to all users
st.markdown(
    """
    <div class="banner">
      <h2>Multi-Domain Intelligence Platform</h2>
      <p>Secure access to cybersecurity, datasets, IT operations, and analytics</p>
      <div class="pillrow">
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Stop here if the user is already logged in
if st.session_state.logged_in:
    st.success(
        f"Already logged in as **{st.session_state.username}** "
        f"(role: {st.session_state.role})."
    )
    st.stop()

# Separate tabs for login and registration
tab_login, tab_register = st.tabs(["Login", "Register"])

with tab_login:
    # Login form
    st.subheader("Login")

    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Log in", type="primary"):
        # Basic input validation
        if not username or not password:
            st.warning("Please enter both username and password.")
        else:
            # Attempt authentication
            user = auth.login_user(username, password)
            if user is None:
                st.error("Login failed. Invalid username or password.")
            else:
                # Persist login state
                st.session_state.logged_in = True
                st.session_state.username = user.get_username()
                st.session_state.role = user.get_role()
                st.success(f"Welcome, {user.get_username()} (role: {user.get_role()})")
                st.rerun()

with tab_register:
    # Registration form
    st.subheader("Register")

    new_username = st.text_input("Choose a username", key="register_username")
    new_password = st.text_input("Choose a password", type="password", key="register_password")
    confirm_password = st.text_input("Confirm password", type="password", key="register_confirm")
    role = st.selectbox("Role", ["user", "analyst", "admin"], key="register_role")

    if st.button("Create account"):
        # Check required fields
        if not new_username or not new_password or not confirm_password:
            st.warning("Please fill in all fields.")
        elif new_password != confirm_password:
            st.error("Passwords do not match.")
        else:
            try:
                # Create the new user account
                auth.register_user(new_username, new_password, role)
                st.success(f"User **{new_username}** created. You can now log in.")
            except sqlite3.IntegrityError:
                # Username already exists
                st.error("That username already exists.")
            except Exception as e:
                # Catch-all for unexpected issues
                st.error(f"Could not create user: {e}")
