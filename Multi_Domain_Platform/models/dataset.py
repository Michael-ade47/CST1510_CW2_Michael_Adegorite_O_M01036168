from __future__ import annotations

# Core Python bits
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Any, List, Tuple

# Data + UI libraries
import pandas as pd
import streamlit as st

# Local service for the chat/AI feature
from services.ai_assistant import AIAssistant


# Build a compact summary of what the user is looking at (used by the AI assistant)
def build_dataset_context(all_df: pd.DataFrame, filtered_df: pd.DataFrame, selected_chart: str) -> str:
    # Small helper: value counts for a column, safely
    def vc(df: pd.DataFrame, col: str, n: int = 8) -> list[tuple[str, int]]:
        # If the data/column isn't available, just return nothing
        if df is None or df.empty or col not in df.columns:
            return []
        # Normalise values and grab the top N counts
        s = df[col].astype(str).fillna("Unknown").value_counts().head(n)
        return list(zip(s.index.tolist(), s.values.tolist()))

    # Totals (guarded so None doesn't crash)
    total_all = 0 if all_df is None else len(all_df)
    total_filtered = 0 if filtered_df is None else len(filtered_df)

    # Quick breakdowns that usually matter on this page
    source_counts = vc(filtered_df, "source")
    category_counts = vc(filtered_df, "category")

    # Build context lines in a readable way
    lines = []
    lines.append("Datasets dashboard context")            # header line for clarity
    lines.append(f"Selected chart: {selected_chart}")    # what visual the user chose
    lines.append(f"All datasets: {total_all}")           # total rows in DB view
    lines.append(f"Filtered datasets: {total_filtered}") # total after filters

    # Include breakdowns only when we actually have them
    if source_counts:
        lines.append("Source counts (filtered): " + "; ".join([f"{k}={v}" for k, v in source_counts]))
    if category_counts:
        lines.append("Category counts (filtered): " + "; ".join([f"{k}={v}" for k, v in category_counts]))

    # Final text block fed into the assistant
    return "\n".join(lines)


# Lightweight domain object for one dataset record
@dataclass(slots=True)
class Dataset:
    id: int
    dataset_name: str
    category: str
    source: str
    last_updated: Optional[str] = None
    record_count: int = 0
    file_size_mb: float = 0.0
    created_at: Optional[str] = None

    # Friendly label for dropdowns/logs
    def __str__(self) -> str:
        return f"{self.dataset_name} ({self.source})"


# Repository wrapper around the datasets_metadata table
class DatasetRepository:
    TABLE = "datasets_metadata"  # DB table name
    COLS = [
        "id",
        "dataset_name",
        "category",
        "source",
        "last_updated",
        "record_count",
        "file_size_mb",
        "created_at",
    ]

    def __init__(self, db: Any):
        # db is expected to expose fetch_all / fetch_one / execute_query
        self.db = db

    # Read everything into a DataFrame (nice for filtering + charts)
    def read_all_df(self) -> pd.DataFrame:
        rows = self.db.fetch_all(
            f"""
            SELECT {", ".join(self.COLS)}
            FROM {self.TABLE}
            ORDER BY id DESC
            """
        )

        # Build a DataFrame even when empty (keeps downstream code simpler)
        df = pd.DataFrame(rows, columns=self.COLS) if rows else pd.DataFrame(columns=self.COLS)

        # Parse timestamps so charts/sorting behave properly
        if "last_updated" in df.columns:
            df["last_updated"] = pd.to_datetime(df["last_updated"], errors="coerce")
        if "created_at" in df.columns:
            df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

        return df

    # Insert a new dataset record
    def create(
        self,
        dataset_name: str,
        category: str,
        source: str,
        last_updated: str,
        record_count: int,
        file_size_mb: float,
    ) -> Optional[int]:
        # Timestamp the record creation on insert
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.db.execute_query(
            f"""
            INSERT INTO {self.TABLE}
                (dataset_name, category, source, last_updated, record_count, file_size_mb, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_name,
                category,
                source,
                last_updated,
                int(record_count),
                float(file_size_mb),
                created_at,
            ),
        )

        # Return the DB row id so the UI can confirm what happened
        row = self.db.fetch_one("SELECT last_insert_rowid()")
        return int(row[0]) if row else None

    # Update an existing dataset record by id
    def update(
        self,
        dataset_id: int,
        dataset_name: str,
        category: str,
        source: str,
        last_updated: str,
        record_count: int,
        file_size_mb: float,
    ) -> None:
        self.db.execute_query(
            f"""
            UPDATE {self.TABLE}
            SET dataset_name = ?,
                category = ?,
                source = ?,
                last_updated = ?,
                record_count = ?,
                file_size_mb = ?
            WHERE id = ?
            """,
            (
                dataset_name,
                category,
                source,
                last_updated,
                int(record_count),
                float(file_size_mb),
                int(dataset_id),
            ),
        )

    # Delete a dataset record by id
    def delete(self, dataset_id: int) -> None:
        self.db.execute_query(
            f"DELETE FROM {self.TABLE} WHERE id = ?",
            (int(dataset_id),),
        )


# Sidebar UI for filtering datasets
class DatasetFilterPanel:
    def render(self, df: pd.DataFrame) -> Tuple[List[str], List[str]]:
        with st.sidebar:
            st.header("Dataset Filters")

            # Filter by source (if available)
            source = (
                st.multiselect("Source", sorted(df["source"].dropna().unique()), key="ds_filter_source")
                if "source" in df.columns
                else []
            )

            # Filter by dataset name (if available)
            name = (
                st.multiselect("Dataset Name", sorted(df["dataset_name"].dropna().unique()), key="ds_filter_name")
                if "dataset_name" in df.columns
                else []
            )

        return source, name


# Filter logic kept separate from the UI
class DatasetFilter:
    @staticmethod
    def apply(df: pd.DataFrame, source: List[str], names: List[str]) -> pd.DataFrame:
        out = df.copy()  # avoid mutating the original table

        # Apply source filter if selected
        if source and "source" in out.columns:
            out = out[out["source"].isin(source)]

        # Apply name filter if selected
        if names and "dataset_name" in out.columns:
            out = out[out["dataset_name"].isin(names)]

        return out


# CRUD UI for datasets (create/view/update/delete)
class DatasetOptions:
    def __init__(self, repo: DatasetRepository, df: pd.DataFrame):
        self.repo = repo
        self.df = df

    # Main entry: choose which action you want
    def render(self, mode: str, on_mode_change):
        st.subheader("Dataset Actions")

        choice = st.radio(
            "Choose what you want to do:",
            ["Create dataset", "Read dataset details", "Update dataset", "Delete dataset"],
            horizontal=True,
            key="ds_crud_choice",
        )

        # Keep UI labels separate from internal mode keys
        mapping = {
            "Create dataset": "create",
            "Read dataset details": "view",
            "Update dataset": "update",
            "Delete dataset": "delete",
        }
        selected_mode = mapping[choice]
        on_mode_change(selected_mode)

        st.markdown("---")

        # Dispatch to the matching handler
        getattr(self, f"_{selected_mode}")()

    # Build dropdown options like: "12 | malware-feed | GitHub"
    def _build_options(self) -> List[str]:
        if self.df is None or self.df.empty or "id" not in self.df.columns:
            return []
        return self.df.apply(
            lambda r: f"{int(r['id'])} | {r.get('dataset_name','')} | {r.get('source','')}",
            axis=1,
        ).tolist()

    # Create form
    def _create(self):
        with st.form("create_dataset_form"):
            dataset_name = st.text_input("Dataset Name")
            category = st.text_input("Category")
            source = st.text_input("Source")
            last_updated = st.date_input("Last Updated Date", value=date.today())
            record_count = st.number_input("Record Count", min_value=0, step=1)
            file_size_mb = st.number_input("File Size (MB)", min_value=0.0, step=0.1, format="%.1f")
            submitted = st.form_submit_button("Add Dataset")

        # Validate then insert
        if submitted:
            if not dataset_name.strip():
                st.error("Dataset name is required.")
                return
            if not category.strip():
                st.error("Category is required.")
                return
            if not source.strip():
                st.error("Source is required.")
                return

            new_id = self.repo.create(
                dataset_name=dataset_name.strip(),
                category=category.strip(),
                source=source.strip(),
                last_updated=last_updated.strftime("%Y-%m-%d"),
                record_count=int(record_count),
                file_size_mb=float(file_size_mb),
            )
            st.success(f"Dataset '{dataset_name}' added successfully! (ID: {new_id})")
            st.rerun()

    # Delete flow with confirmation
    def _delete(self):
        options = self._build_options()
        if not options:
            st.info("No datasets available to delete.")
            return

        selected = st.selectbox("Select a dataset to delete:", options, key="delete_dataset_select")
        dataset_id = int(selected.split("|")[0].strip())

        confirm = st.checkbox("Yes, I really want to delete this dataset record.", key="confirm_delete_ds")
        if st.button("Delete Dataset", key="btn_confirm_delete_dataset"):
            if not confirm:
                st.warning("Please confirm that you want to delete this dataset.")
                return
            self.repo.delete(dataset_id)
            st.success(f"Dataset record with ID {dataset_id} deleted successfully!")
            st.rerun()

    # Update flow (pre-fills existing values)
    def _update(self):
        options = self._build_options()
        if not options:
            st.info("No datasets available to update.")
            return

        selected = st.selectbox("Select a dataset to update:", options, key="update_dataset_select")
        dataset_id = int(selected.split("|")[0].strip())
        row = self.df[self.df["id"] == dataset_id].iloc[0]

        # If last_updated is missing, fall back to today
        last_updated_default = (
            date.today() if pd.isna(row.get("last_updated"))
            else pd.to_datetime(row["last_updated"]).date()
        )

        with st.form("update_dataset_form"):
            dataset_name = st.text_input("Dataset Name", value=str(row.get("dataset_name", "")))
            category = st.text_input("Category", value=str(row.get("category", "")))
            source = st.text_input("Source", value=str(row.get("source", "")))
            last_updated = st.date_input("Last Updated Date", value=last_updated_default)

            record_count = st.number_input(
                "Record Count",
                min_value=0,
                step=1,
                value=int(row["record_count"]) if not pd.isna(row.get("record_count")) else 0,
            )

            file_size_mb = st.number_input(
                "File Size (MB)",
                min_value=0.0,
                step=0.1,
                format="%.1f",
                value=float(row["file_size_mb"]) if not pd.isna(row.get("file_size_mb")) else 0.0,
            )

            # Created_at is shown for context but not editable
            st.text_input("Created At (read-only)", value=str(row.get("created_at", "")), disabled=True)
            submitted = st.form_submit_button("Update Dataset")

        if submitted:
            if not dataset_name.strip():
                st.error("Dataset name is required.")
                return
            if not category.strip():
                st.error("Category is required.")
                return
            if not source.strip():
                st.error("Source is required.")
                return

            self.repo.update(
                dataset_id=dataset_id,
                dataset_name=dataset_name.strip(),
                category=category.strip(),
                source=source.strip(),
                last_updated=last_updated.strftime("%Y-%m-%d"),
                record_count=int(record_count),
                file_size_mb=float(file_size_mb),
            )
            st.success(f"Dataset ID {dataset_id} updated successfully!")
            st.rerun()

    # Read-only detail view
    def _view(self):
        options = self._build_options()
        if not options:
            st.info("No datasets available to view.")
            return

        selected = st.selectbox("Select a dataset to view:", options, key="view_dataset_select")
        dataset_id = int(selected.split("|")[0].strip())
        row = self.df[self.df["id"] == dataset_id].iloc[0]

        st.markdown("### Dataset Details")
        c1, c2 = st.columns(2)

        # Left column: identity fields
        with c1:
            st.text_input("Dataset ID", value=str(row.get("id", "")), disabled=True)
            st.text_input("Dataset Name", value=str(row.get("dataset_name", "")), disabled=True)
            st.text_input("Category", value=str(row.get("category", "")), disabled=True)
            st.text_input("Source", value=str(row.get("source", "")), disabled=True)

        # Right column: metadata fields
        with c2:
            st.text_input("Last Updated", value=str(row.get("last_updated", "")), disabled=True)
            st.text_input("Record Count", value=str(row.get("record_count", "")), disabled=True)
            st.text_input("File Size (MB)", value=str(row.get("file_size_mb", "")), disabled=True)
            st.text_input("Created At", value=str(row.get("created_at", "")), disabled=True)


# Data science assistant panel (uses dashboard context)
class DataScienceChat:
    # System prompt steers the assistant to stay on-topic
    SYSTEM_PROMPT = (
        "You are a Data Science expert. "
        "Use the provided datasets dashboard context to answer questions about filters, charts, and dataset metadata. "
        "Explain data cleaning, EDA, visualisation, and machine learning clearly with practical examples."
    )

    # Ensure chat objects exist in session state
    def init(self) -> None:
        st.session_state.setdefault("ds_chat", AIAssistant(system_prompt=self.SYSTEM_PROMPT))
        st.session_state.setdefault("ds_messages", [])

    # Send one user message + store the assistant reply
    def send(self, message: str) -> None:
        message = (message or "").strip()
        if not message:
            return

        self.init()
        assistant = st.session_state["ds_chat"]

        # Context lets the assistant answer using the same filters/charts the user sees
        context = (st.session_state.get("ds_ai_context") or "").strip()
        payload = f"{context}\n\nUser question: {message}" if context else message

        st.session_state["ds_messages"].append({"role": "user", "content": message})
        st.session_state["ds_messages"].append(
            {"role": "assistant", "content": assistant.send_message(payload)}
        )
        st.session_state["ds_ai_input"] = ""

    # Clear chat history (keeps the assistant instance)
    def clear(self) -> None:
        st.session_state["ds_messages"] = []

    # Render the panel only when it's meant to be visible
    def render(self, visible: bool) -> None:
        if not visible:
            return

        st.subheader("Data Science AI Assistant")

        col1, col2 = st.columns([5, 1])
        with col1:
            st.text_input(
                "Ask a data science question",
                key="ds_ai_input",
                on_change=lambda: self.send(st.session_state.get("ds_ai_input", "")),
            )
        with col2:
            st.button("Clear", on_click=self.clear)

        # Show the back-and-forth messages
        for msg in st.session_state.get("ds_messages", []):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])


# Small helper to initialise session defaults in one place
class StateManager:
    def __init__(self, defaults: dict):
        self.defaults = defaults

    # Add missing keys without overwriting existing values
    def init(self) -> None:
        for k, v in self.defaults.items():
            st.session_state.setdefault(k, v)


# Simple auth gate used by pages
class AuthGuard:
    @staticmethod
    def require_login(login_page: str = "Home.py") -> None:
        if not st.session_state.get("logged_in", False):
            st.error("You must be logged in to view this page.")
            if st.button("Go to login page", key="btn_go_login"):
                st.switch_page(login_page)
            st.stop()
