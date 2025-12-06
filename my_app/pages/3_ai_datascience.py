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

    fig_source = px.bar(
        source_counts,
        x="Source",
        y="Count",
        title="Datasets by Source",
        text="Count",
    )
    fig_source.update_traces(textposition="outside")
    fig_source.update_layout(yaxis_title="Number of Datasets")

    st.plotly_chart(fig_source, use_container_width=True)
st.subheader("Add New Dataset Record")

st.subheader("Add New Dataset")

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
            value=int(selected_row["record_count"]) if not pd.isna(selected_row["record_count"]) else 0,
        )

        file_size_mb = st.number_input(
            "File Size (MB)",
            min_value=0.0,
            step=0.1,
            format="%.1f",
            value=float(selected_row["file_size_mb"]) if not pd.isna(selected_row["file_size_mb"]) else 0.0,
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
                    f" Dataset ID {selected_dataset_id} updated successfully!"
                )
                st.rerun()
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

    




st.divider()
if st.button("Log out"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.info("You have been logged out.")
    st.switch_page("Home.py")
