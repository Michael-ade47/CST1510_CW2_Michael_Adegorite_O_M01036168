import streamlit as st
from auth import login_user, register_user  

st.set_page_config(page_title="Login / Register", page_icon="🔑", layout="centered")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""

st.title("🔐 Welcome")

if st.session_state.logged_in:
    st.success(f"Already logged in as **{st.session_state.username}**.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cyber Security Dashboard"):
            st.switch_page("pages/1_cyber_security.py")

    with col2:
        if st.button("IT Tickets Dashboard"):
            st.switch_page("pages/2_IT.py")

    st.stop()

tab_login, tab_register = st.tabs(["Login", "Register"])

# ---------------- LOGIN TAB ---------------- #
with tab_login:
    st.subheader("Login")

    login_username = st.text_input("Username", key="login_username")
    login_password = st.text_input("Password", type="password", key="login_password")

    if st.button("Log in", type="primary"):
        if not login_username or not login_password:
            st.warning("Please enter both username and password.")
        else:
            success, msg = login_user(login_username, login_password)

            if success:
                st.session_state.logged_in = True
                st.session_state.username = login_username
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

# ---------------- REGISTER TAB ---------------- #
with tab_register:
    st.subheader("Register")

    new_username = st.text_input("Choose a username", key="register_username")
    new_password = st.text_input("Choose a password", type="password", key="register_password")
    confirm_password = st.text_input("Confirm password", type="password", key="register_confirm")

    if st.button("Create account"):
        if not new_username or not new_password:
            st.warning("Please fill in all fields.")
        elif new_password != confirm_password:
            st.error("Passwords do not match.")
        else:
            success, msg = register_user(new_username, new_password)

            if success:
                st.success(msg)
            else:
                st.error(msg)