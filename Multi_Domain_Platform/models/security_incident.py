from __future__ import annotations

# Data container + typing
from dataclasses import dataclass
from typing import Optional, Any

# Data + UI
import pandas as pd
import streamlit as st

# Local AI wrapper
from services.ai_assistant import AIAssistant


# Build a short, structured summary of the current dashboard view (used as AI context)
def build_cyber_context(all_df: pd.DataFrame, filtered_df: pd.DataFrame, selected_chart: str) -> str:
    # Safe value-count helper (returns top N counts for a column)
    def vc(df: pd.DataFrame, col: str, n: int = 8) -> list[tuple[str, int]]:
        # If the frame/column isn't there, don't crash the whole page
        if df is None or df.empty or col not in df.columns:
            return []
        # Normalise values a bit and count
        s = df[col].astype(str).fillna("Unknown").value_counts().head(n)
        return list(zip(s.index.tolist(), s.values.tolist()))

    # Convert to int without throwing exceptions
    def safe_int(x) -> int:
        try:
            return int(x)
        except Exception:
            return 0

    # High-level totals
    total_all = 0 if all_df is None else len(all_df)
    total_filtered = 0 if filtered_df is None else len(filtered_df)

    # Quick risk signal: high + critical count
    high_critical = 0
    if filtered_df is not None and not filtered_df.empty and "severity" in filtered_df.columns:
        high_critical = safe_int(filtered_df[filtered_df["severity"].isin(["High", "Critical"])].shape[0])

    # Operational signal: open + in progress count
    open_inprog = 0
    if filtered_df is not None and not filtered_df.empty and "status" in filtered_df.columns:
        open_inprog = safe_int(filtered_df[filtered_df["status"].isin(["Open", "In Progress"])].shape[0])

    # Breakdown counts for quick summaries
    sev_counts = vc(filtered_df, "severity")
    status_counts = vc(filtered_df, "status")
    type_counts = vc(filtered_df, "incident_type")

    # Trend view for the last 14 days (only if we have dates)
    last14 = []
    if filtered_df is not None and not filtered_df.empty and "date" in filtered_df.columns:
        tmp = filtered_df.copy()
        tmp["date"] = pd.to_datetime(tmp["date"], errors="coerce")

        # Strip timezone if present (keeps grouping stable)
        if pd.api.types.is_datetime64tz_dtype(tmp["date"]):
            tmp["date"] = tmp["date"].dt.tz_convert(None)
        else:
            # Some inputs might be timezone-aware later; this keeps it predictable
            try:
                tmp["date"] = tmp["date"].dt.tz_localize(None)
            except Exception:
                pass

        # Remove rows with invalid dates
        tmp = tmp.dropna(subset=["date"])

        if not tmp.empty:
            # Rolling window: today back 13 days = 14 days total
            cutoff = pd.Timestamp.now().normalize() - pd.Timedelta(days=13)
            tmp = tmp[tmp["date"] >= cutoff]
            daily = tmp.groupby(tmp["date"].dt.date).size()
            last14 = [(str(k), safe_int(v)) for k, v in daily.items()]

    # Context lines are kept simple so the AI can read them quickly
    lines = []
    lines.append("Cyber dashboard context")  # header
    lines.append(f"Selected chart: {selected_chart}")
    lines.append(f"All incidents: {total_all}")
    lines.append(f"Filtered incidents: {total_filtered}")
    lines.append(f"High/Critical (filtered): {high_critical}")
    lines.append(f"Open/In Progress (filtered): {open_inprog}")

    # Only add breakdowns when available
    if sev_counts:
        lines.append("Severity counts (filtered): " + "; ".join([f"{k}={v}" for k, v in sev_counts]))
    if status_counts:
        lines.append("Status counts (filtered): " + "; ".join([f"{k}={v}" for k, v in status_counts]))
    if type_counts:
        lines.append("Top incident types (filtered): " + "; ".join([f"{k}={v}" for k, v in type_counts]))
    if last14:
        lines.append("Incidents over last 14 days (filtered): " + "; ".join([f"{d}={c}" for d, c in last14]))

    return "\n".join(lines)


# Simple incident model (useful for typing and printing)
@dataclass(slots=True)
class SecurityIncident:
    id: int
    date: Optional[str] = None
    incident_type: str = ""
    severity: str = ""
    status: str = ""
    description: str = ""
    reported_by: Optional[str] = None

    # Convert severity labels into an ordering value
    def severity_level(self) -> int:
        mapping = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        return mapping.get((self.severity or "").strip().lower(), 0)

    # Friendly one-line description for logs/debug
    def __str__(self) -> str:
        sev = (self.severity or "").strip().upper()
        return f"Incident {self.id} [{sev}] {self.description}"


# Repository: DB access for incidents
class IncidentRepository:
    TABLE = "cyber_incidents"  # DB table name
    COLS = ["id", "date", "incident_type", "severity", "status", "description", "reported_by"]

    def __init__(self, db: Any):
        self.db = db

    # Fetch everything as a DataFrame (works well with filters + charts)
    def fetch_all_df(self) -> pd.DataFrame:
        rows = self.db.fetch_all(
            f"SELECT {', '.join(self.COLS)} FROM {self.TABLE} ORDER BY id DESC"
        )
        df = pd.DataFrame(rows, columns=self.COLS) if rows else pd.DataFrame(columns=self.COLS)

        # Normalise date column so comparisons/grouping work
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")

        return df

    # Insert a new incident record
    def insert(
        self,
        date_: str,
        incident_type: str,
        severity: str,
        status: str,
        description: str,
        reported_by: Optional[str] = None,
    ) -> Optional[int]:
        self.db.execute_query(
            f"""
            INSERT INTO {self.TABLE}
                (date, incident_type, severity, status, description, reported_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (date_, incident_type, severity, status, description, reported_by),
        )
        # Return new row id (handy for UI confirmations)
        row = self.db.fetch_one("SELECT last_insert_rowid()")
        return int(row[0]) if row else None

    # Update only the status field (simple and safe)
    def update_status(self, incident_id: int, new_status: str) -> None:
        self.db.execute_query(
            f"UPDATE {self.TABLE} SET status = ? WHERE id = ?",
            (new_status, incident_id),
        )

    # Delete an incident by id
    def delete(self, incident_id: int) -> None:
        self.db.execute_query(
            f"DELETE FROM {self.TABLE} WHERE id = ?",
            (incident_id,),
        )


# Session-state defaults in one place
class StateManager:
    def __init__(self, defaults: dict):
        self.defaults = defaults

    # Populate missing keys without overwriting existing values
    def init(self) -> None:
        for k, v in self.defaults.items():
            st.session_state.setdefault(k, v)


# Simple login gate to protect the page
class AuthGuard:
    @staticmethod
    def require_login(login_page: str = "Home.py") -> None:
        if not st.session_state.get("logged_in", False):
            st.error("You must be logged in to view the dashboard.")
            if st.button("Go to login page", key="btn_go_login"):
                st.switch_page(login_page)
            st.stop()


# Sidebar filter controls
class FilterPanel:
    def render_basic(self):
        with st.sidebar:
            st.header("Filters")

            # Filter by severity
            sev = st.multiselect(
                "Severity",
                ["Low", "Medium", "High", "Critical"],
                default=[],
                key="filter_sev",
            )

            # Filter by incident status
            status = st.multiselect(
                "Status",
                ["Open", "In Progress", "Resolved", "Closed"],
                default=[],
                key="filter_status",
            )

        return sev, status


# Apply filter selections to the DataFrame
class IncidentFilter:
    @staticmethod
    def apply_basic(df, sev, status):
        out = df.copy()  # keep the original untouched

        # Apply only when the user selected values
        if sev and "severity" in out.columns:
            out = out[out["severity"].isin(sev)]

        if status and "status" in out.columns:
            out = out[out["status"].isin(status)]

        return out


# Build selectbox labels so users don't have to guess IDs
class IncidentOptions:
    @staticmethod
    def build(df: pd.DataFrame, include_severity: bool = True):
        ids, labels = [], {}

        # If no data, return empty options safely
        if df is None or df.empty or "id" not in df.columns:
            return ids, labels

        for _, row in df.iterrows():
            inc_id = row["id"]
            t = row.get("incident_type", "N/A")
            s = row.get("status", "Unknown")

            # Some screens want severity in the label, others don't
            if include_severity:
                sev = row.get("severity", "Unknown")
                label = f"#{inc_id} – {t} [{sev}, {s}]"
            else:
                label = f"#{inc_id} – {t} [{s}]"

            ids.append(inc_id)
            labels[inc_id] = label

        return ids, labels


# Chat UI for cybersecurity questions
class CyberChat:
    SYSTEM_PROMPT = (
        "You are a cyber security expert. "
        "Use the provided dashboard context to answer questions about incidents, filters, and charts. "
        "Explain clearly and relate answers to incident response, SIEM, and threat detection."
    )

    # Create chat state if missing
    def init(self) -> None:
        st.session_state.setdefault("cyber_chat", AIAssistant(system_prompt=self.SYSTEM_PROMPT))
        st.session_state.setdefault("cyber_messages", [])

    # Send one message and store the response
    def send(self, message: str) -> None:
        message = (message or "").strip()
        if not message:
            return

        self.init()
        assistant = st.session_state["cyber_chat"]

        # Attach dashboard context so answers match what the user sees
        context = (st.session_state.get("cyber_ai_context") or "").strip()
        payload = f"{context}\n\nUser question: {message}" if context else message

        st.session_state["cyber_messages"].append({"role": "user", "content": message})
        st.session_state["cyber_messages"].append(
            {"role": "assistant", "content": assistant.send_message(payload)}
        )
        st.session_state["cyber_ai_input"] = ""

    # Clear just the visible history
    def clear(self) -> None:
        st.session_state["cyber_messages"] = []

    # Render chat only when panel is visible
    def render(self, visible: bool) -> None:
        if not visible:
            return

        st.subheader("Cyber Security AI Assistant")

        col1, col2 = st.columns([5, 1])
        with col1:
            st.text_input(
                "Ask a cyber security question",
                key="cyber_ai_input",
                on_change=lambda: self.send(st.session_state.get("cyber_ai_input", "")),
            )
        with col2:
            st.button("Clear", on_click=self.clear)

        for msg in st.session_state.get("cyber_messages", []):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        