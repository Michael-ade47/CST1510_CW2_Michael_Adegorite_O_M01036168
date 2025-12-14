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
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date


from app.data.datasets import read_all_datasets, create_dataset, delete_dataset, update_dataset


st.set_page_config(page_title="Datasets", page_icon="📁", layout="wide")


if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.error("You must be logged in to view this page.")
    if st.button("Go to login page"):
        st.switch_page("Home.py")
    st.stop()


st.title("Datasets")
st.success(f"Hello, **{st.session_state.username}**! Here are all available datasets.")
if "active_dataset_form" not in st.session_state:
    st.session_state.active_dataset_form = None

if "show_dataset_crud" not in st.session_state:
    st.session_state.show_dataset_crud = False


try:
    datasets = read_all_datasets()
except Exception as e:
    st.error(f"Error loading datasets: {e}")
    datasets = pd.DataFrame()

if datasets.empty:
    st.info("No datasets found in the database.")
    st.stop()


with st.sidebar:
    st.header("Dataset Filters")

    if "source" in datasets.columns:
        source_options = sorted(datasets["source"].dropna().unique())
        source_filter = st.multiselect("Source", source_options)
    else:
        source_filter = []

    if "name" in datasets.columns:
        name_options = sorted(datasets["name"].dropna().unique())
        name_filter = st.multiselect("Dataset Name", name_options)
    else:
        name_filter = []


filtered = datasets.copy()

if source_filter and "source" in filtered.columns:
    filtered = filtered[filtered["source"].isin(source_filter)]

if name_filter and "name" in filtered.columns:
    filtered = filtered[filtered["name"].isin(name_filter)]


st.subheader("Datasets Table (Filtered)")
st.caption(f"Showing **{len(filtered)}** of {len(datasets)} total datasets.")
st.dataframe(filtered, use_container_width=True)


if "source" in filtered.columns:
    st.subheader("Datasets by Source")

    source_counts = filtered["source"].value_counts().reset_index()
    source_counts.columns = ["Source", "Count"]

    fig_source = px.pie(
        source_counts,
        names="Source",
        values="Count",
        title="Datasets by Source",
        hole=0.4,
        color="Source",
        color_discrete_sequence=px.colors.qualitative.Set3,
    )

    fig_source.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig_source, use_container_width=True)

if "category" in filtered.columns and "record_count" in filtered.columns:
    st.subheader("Category Radar – Total Record Count")

    radar_df = (
        filtered.groupby("category", as_index=False)["record_count"]
        .sum()
        .sort_values("record_count", ascending=False)
    )

    fig_radar = px.line_polar(
        radar_df,
        r="record_count",
        theta="category",
        line_close=True,
        title="Total Record Count by Category (Radar View)",
    )
    fig_radar.update_traces(fill="toself")
    st.plotly_chart(fig_radar, use_container_width=True)


    st.subheader("Dataset Actions")

if st.button(" Show / Hide Dataset CRUD Tools"):
    st.session_state.show_dataset_crud = not st.session_state.show_dataset_crud
    if not st.session_state.show_dataset_crud:
        st.session_state.active_dataset_form = None

if st.session_state.show_dataset_crud:
    st.caption("Choose which dataset action you want to perform:")

    b1, b2, b3, b4 = st.columns(4)

    with b1:
        if st.button("Create dataset", key="btn_create_dataset"):
            st.session_state.active_dataset_form = "create"

    with b2:
        if st.button("Delete dataset", key="btn_delete_dataset"):
            st.session_state.active_dataset_form = "delete"

    with b3:
        if st.button("Update dataset", key="btn_update_dataset"):
            st.session_state.active_dataset_form = "update"

    with b4:
        if st.button("View details", key="btn_view_dataset"):
            st.session_state.active_dataset_form = "view"

st.markdown("---")

if st.session_state.active_dataset_form == "create":
    st.subheader("Create New Dataset")

    with st.form("create_dataset_form"):
        dataset_name = st.text_input("Dataset Name")
        category = st.text_input("Category")
        source = st.text_input("Source")
        last_updated_date = st.date_input("Last Updated Date")
        record_count = st.number_input(
            "Record Count",
            min_value=0,
            step=1,
        )
        file_size_mb = st.number_input(
            "File Size (MB)",
            min_value=0.0,
            step=0.1,
            format="%.1f",
        )

        submit_dataset = st.form_submit_button("Add Dataset")

    if submit_dataset:
        if not dataset_name:
            st.error("Dataset name is required.")
        elif not category:
            st.error("Category is required.")
        elif not source:
            st.error("Source is required.")
        else:
            last_updated_str = last_updated_date.strftime("%Y-%m-%d")
            created_at_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            dataset_fields = {
                "dataset_name": dataset_name,
                "category": category,
                "source": source,
                "last_updated": last_updated_str,
                "record_count": int(record_count),
                "file_size_mb": float(file_size_mb),
                "created_at": created_at_str,
            }

            new_id = create_dataset(**dataset_fields)

            st.success(
                f"Dataset '{dataset_name}' added successfully! (ID: {new_id})"
            )
            st.rerun()

elif st.session_state.active_dataset_form == "delete":
    st.subheader("Delete Dataset Record")

    datasets_df = read_all_datasets()

    if datasets_df.empty:
        st.info("No dataset records available to delete.")
    else:
        delete_options = datasets_df.apply(
            lambda row: f"{row['id']} | {row['dataset_name']} | {row['source']}",
            axis=1,
        )

        selected_delete = st.selectbox(
            "Select a dataset to delete:",
            delete_options,
            key="delete_dataset_select",
        )

        selected_id_str = selected_delete.split("|")[0].strip()
        selected_dataset_id = int(selected_id_str)

        confirm_delete = st.checkbox(
            "Yes, I really want to delete this dataset record."
        )

        if st.button("Delete Dataset"):
            if not confirm_delete:
                st.warning("Please confirm that you want to delete this dataset.")
            else:
                deleted_rows = delete_dataset(selected_dataset_id)

                if deleted_rows == 0:
                    st.error("No dataset was deleted. Please check the selected record.")
                else:
                    st.success(
                        f"Dataset record with ID {selected_dataset_id} deleted successfully!"
                    )
                    st.rerun()

elif st.session_state.active_dataset_form == "update":
    st.subheader("Update Dataset Record")

    datasets_df = read_all_datasets()

    if datasets_df.empty:
        st.info("No dataset records available to update.")
    else:
        update_options = datasets_df.apply(
            lambda row: f"{row['id']} | {row['dataset_name']} | {row['source']}",
            axis=1,
        )

        selected_update = st.selectbox(
            "Select a dataset to update:",
            update_options,
            key="update_dataset_select",
        )

        selected_id_str = selected_update.split("|")[0].strip()
        selected_dataset_id = int(selected_id_str)

        selected_row = datasets_df[datasets_df["id"] == selected_dataset_id].iloc[0]

        if pd.isna(selected_row["last_updated"]):
            last_updated_default = date.today()
        else:
            last_updated_default = pd.to_datetime(selected_row["last_updated"]).date()

        with st.form("update_dataset_form"):
            dataset_name = st.text_input(
                "Dataset Name",
                value=selected_row["dataset_name"],
            )
            category = st.text_input(
                "Category",
                value=selected_row["category"],
            )
            source = st.text_input(
                "Source",
                value=selected_row["source"],
            )
            last_updated_date = st.date_input(
                "Last Updated Date",
                value=last_updated_default,
            )
            record_count = st.number_input(
                "Record Count",
                min_value=0,
                step=1,
                value=int(selected_row["record_count"])
                if not pd.isna(selected_row["record_count"])
                else 0,
            )
            file_size_mb = st.number_input(
                "File Size (MB)",
                min_value=0.0,
                step=0.1,
                format="%.1f",
                value=float(selected_row["file_size_mb"])
                if not pd.isna(selected_row["file_size_mb"])
                else 0.0,
            )

            st.text_input(
                "Created At (read-only)",
                value=str(selected_row["created_at"]),
                disabled=True,
            )

            submit_update = st.form_submit_button("Update Dataset")

        if submit_update:
            if not dataset_name:
                st.error("Dataset name is required.")
            elif not category:
                st.error("Category is required.")
            elif not source:
                st.error("Source is required.")
            else:
                last_updated_str = last_updated_date.strftime("%Y-%m-%d")

                update_fields = {
                    "dataset_name": dataset_name,
                    "category": category,
                    "source": source,
                    "last_updated": last_updated_str,
                    "record_count": int(record_count),
                    "file_size_mb": float(file_size_mb),
                }

                rows_updated = update_dataset(selected_dataset_id, **update_fields)

                if rows_updated == 0:
                    st.error("No dataset was updated. Please check the selected record.")
                else:
                    st.success(
                        f"Dataset ID {selected_dataset_id} updated successfully!"
                    )
                    st.rerun()

elif st.session_state.active_dataset_form == "view":
    st.subheader("Read Dataset Record")

    datasets_df = read_all_datasets()

    if datasets_df.empty:
        st.info("No dataset records available to view.")
    else:
        view_options = datasets_df.apply(
            lambda row: f"{row['id']} | {row['dataset_name']} | {row['source']}",
            axis=1,
        )

        selected_view = st.selectbox(
            "Select a dataset to view:",
            view_options,
            key="view_dataset_select",
        )

        selected_id_str = selected_view.split("|")[0].strip()
        selected_dataset_id = int(selected_id_str)

        selected_row = datasets_df[datasets_df["id"] == selected_dataset_id].iloc[0]

        st.markdown("### Dataset Details")

        col1, col2 = st.columns(2)

        with col1:
            st.text_input(
                "Dataset ID",
                value=str(selected_row["id"]),
                disabled=True,
            )
            st.text_input(
                "Dataset Name",
                value=selected_row["dataset_name"],
                disabled=True,
            )
            st.text_input(
                "Category",
                value=selected_row["category"],
                disabled=True,
            )
            st.text_input(
                "Source",
                value=selected_row["source"],
                disabled=True,
            )

        with col2:
            st.text_input(
                "Last Updated",
                value=str(selected_row["last_updated"]),
                disabled=True,
            )
            st.text_input(
                "Record Count",
                value=str(selected_row["record_count"]),
                disabled=True,
            )
            st.text_input(
                "File Size (MB)",
                value=str(selected_row["file_size_mb"]),
                disabled=True,
            )
            st.text_input(
                "Created At",
                value=str(selected_row["created_at"]),
                disabled=True,
            )


    




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
