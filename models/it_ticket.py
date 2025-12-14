from __future__ import annotations

# Standard library imports
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Dict, Any, List, Tuple
from uuid import uuid4

# Third-party imports
import pandas as pd
import streamlit as st

# Internal services
from services.database_manager import DatabaseManager
from services.ai_assistant import AIAssistant


# Public API for this module
__all__ = [
    "ITTicket",
    "ITTicketRepository",
    "StateManager",
    "AuthGuard",
    "TicketOptions",
    "TicketFilterPanel",
    "TicketFilter",
    "ITSupportChat",
    "TicketCRUD",
    "build_it_context",
]


# Lightweight domain model for an IT ticket
@dataclass(slots=True)
class ITTicket:
    id: int
    ticket_id: str
    category: str
    subject: str
    priority: str
    status: str
    description: str
    assigned_to: Optional[str] = None
    created_date: Optional[str] = None

    # Assign the ticket to a staff member
    def assign_to(self, staff: str) -> None:
        self.assigned_to = staff

    # Mark the ticket as closed
    def close(self) -> None:
        self.status = "Closed"

    # Human-readable summary
    def __str__(self) -> str:
        assigned = self.assigned_to or "Unassigned"
        return f"{self.ticket_id}: {self.subject} [{self.priority}] – {self.status} (assigned to: {assigned})"


# Repository layer handling DB access
class ITTicketRepository:
    TABLE = "it_tickets"
    COLS = [
        "id",
        "ticket_id",
        "category",
        "subject",
        "priority",
        "status",
        "description",
        "assigned_to",
        "created_date",
    ]

    def __init__(self, db: DatabaseManager):
        self.db = db

    # Generate a readable unique ticket ID
    def _new_ticket_id(self) -> str:
        stamp = datetime.now().strftime("%Y%m%d")
        short = uuid4().hex[:6].upper()
        return f"IT-{stamp}-{short}"

    # Load all tickets into a DataFrame
    def read_all_df(self) -> pd.DataFrame:
        rows = self.db.fetch_all(
            f"SELECT {', '.join(self.COLS)} FROM {self.TABLE} ORDER BY id DESC"
        )
        df = pd.DataFrame(rows, columns=self.COLS) if rows else pd.DataFrame(columns=self.COLS)

        # Calculate ticket age in days
        if "created_date" in df.columns:
            df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
            df["age_days"] = (pd.Timestamp(date.today()) - df["created_date"]).dt.days
        else:
            df["age_days"] = pd.NA

        return df

    # Insert a new ticket
    def create(
        self,
        created_date: str,
        category: str,
        subject: str,
        priority: str,
        status: str,
        description: str,
        assigned_to: Optional[str] = None,
        ticket_id: Optional[str] = None,
    ) -> Optional[int]:
        ticket_id = ticket_id or self._new_ticket_id()

        self.db.execute_query(
            f"""
            INSERT INTO {self.TABLE}
                (ticket_id, created_date, category, subject, priority, status, description, assigned_to)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ticket_id, created_date, category, subject, priority, status, description, assigned_to),
        )
        row = self.db.fetch_one("SELECT last_insert_rowid()")
        return int(row[0]) if row else None

    # Delete a ticket by internal row ID
    def delete_by_row_id(self, row_id: int) -> None:
        self.db.execute_query(f"DELETE FROM {self.TABLE} WHERE id = ?", (int(row_id),))

    # Update ticket status using public ticket ID
    def update_status(self, ticket_id: str, new_status: str) -> None:
        self.db.execute_query(
            f"UPDATE {self.TABLE} SET status = ? WHERE ticket_id = ?",
            (new_status, ticket_id),
        )


# Centralised session state initialiser
class StateManager:
    def __init__(self, defaults: Dict[str, Any]):
        self.defaults = defaults

    # Ensure all expected session keys exist
    def init(self) -> None:
        for k, v in self.defaults.items():
            st.session_state.setdefault(k, v)


# Simple access guard for protected pages
class AuthGuard:
    @staticmethod
    def require_login(login_page: str = "Home.py") -> None:
        if not st.session_state.get("logged_in", False):
            st.error("You must be logged in to view this page.")
            if st.button("Go to login page", key="btn_go_login"):
                st.switch_page(login_page)
            st.stop()


# Helpers for building readable selectbox options
class TicketOptions:
    @staticmethod
    def safe_fmt(row: pd.Series, template: str) -> str:
        # Replace NaNs to avoid formatting issues
        d = {k: ("" if pd.isna(v) else v) for k, v in row.to_dict().items()}
        try:
            return template.format(**d)
        except Exception:
            return f"{d.get('ticket_id','')} | {d.get('subject','')}"

    @classmethod
    def list(cls, df: pd.DataFrame, template: str) -> List[str]:
        return [cls.safe_fmt(r, template) for _, r in df.iterrows()]


# Sidebar filters for ticket analysis
class TicketFilterPanel:
    def render(self, df: pd.DataFrame) -> Tuple[List[str], List[str], List[str], int]:
        with st.sidebar:
            st.header("Filters – Delays in Resolution")

            status_f = st.multiselect("Status", sorted(df["status"].dropna().unique()))
            priority_f = st.multiselect("Priority", sorted(df["priority"].dropna().unique()))
            assignee_f = st.multiselect("Assigned to", sorted(df["assigned_to"].dropna().unique()))

            max_age = int(df["age_days"].max()) if df["age_days"].notna().any() else 0
            min_age = st.slider("Minimum days open", 0, max_age, 0)

        return status_f, priority_f, assignee_f, min_age


# Apply selected filters to the DataFrame
class TicketFilter:
    @staticmethod
    def apply(df: pd.DataFrame, status_f, priority_f, assignee_f, min_age: int) -> pd.DataFrame:
        out = df.copy()

        for col, vals in [("status", status_f), ("priority", priority_f), ("assigned_to", assignee_f)]:
            if vals:
                out = out[out[col].isin(vals)]

        if min_age > 0:
            out = out[out["age_days"] >= min_age]

        return out


# Build a compact text summary for the AI assistant
def build_it_context(tickets_df: pd.DataFrame, filtered_df: pd.DataFrame) -> str:
    parts = [
        f"Total tickets: {len(tickets_df)}",
        f"Tickets after filters: {len(filtered_df)}",
    ]

    if not filtered_df.empty:
        parts.append(
            "Status breakdown: "
            + ", ".join(f"{k}={v}" for k, v in filtered_df["status"].value_counts().items())
        )
        parts.append(
            "Priority breakdown: "
            + ", ".join(f"{k}={v}" for k, v in filtered_df["priority"].value_counts().items())
        )

    return "\n".join(parts)


# AI chat component for IT support insights
class ITSupportChat:
    CHAT_KEY = "it_chat"
    MSG_KEY = "it_messages"
    INPUT_KEY = "it_ai_input"

    SYSTEM_PROMPT = (
        "You are an IT Support expert helping analyse ticket dashboards. "
        "Explain causes, priorities, and next actions clearly."
    )

    # Initialise chat-related state
    def _init_state(self) -> None:
        st.session_state.setdefault(self.MSG_KEY, [])
        st.session_state.setdefault(self.INPUT_KEY, "")

    # Send a message to the AI assistant
    def send(self) -> None:
        self._init_state()
        msg = st.session_state.get(self.INPUT_KEY, "").strip()
        if not msg:
            return

        assistant = st.session_state.setdefault(
            self.CHAT_KEY, AIAssistant(system_prompt=self.SYSTEM_PROMPT)
        )

        st.session_state[self.MSG_KEY].append({"role": "user", "content": msg})

        with st.spinner("Generating response..."):
            reply = assistant.send_message(msg)

        st.session_state[self.MSG_KEY].append({"role": "assistant", "content": reply})
        st.session_state[self.INPUT_KEY] = ""

    # Clear the chat history
    def clear(self) -> None:
        st.session_state[self.MSG_KEY] = []
        st.session_state.pop(self.CHAT_KEY, None)

    # Render the chat UI
    def render(self, visible: bool) -> None:
        if not visible:
            return

        self._init_state()
        st.subheader("IT AI Assistant")

        st.text_input(
            "Ask an IT support question",
            key=self.INPUT_KEY,
            on_change=self.send,
        )

        for m in st.session_state[self.MSG_KEY]:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])


# CRUD UI for tickets
class TicketCRUD:
    def __init__(self, repo: ITTicketRepository, tickets_df: pd.DataFrame):
        self.repo = repo
        self.df = tickets_df

    # Entry point for the CRUD panel
    def render(self, visible: bool) -> None:
        if not visible:
            return

        st.subheader("Ticket Actions")

        choice = st.radio(
            "Choose an action:",
            ["Create ticket", "Read ticket details", "Update ticket status", "Delete ticket"],
            horizontal=True,
        )

        if choice == "Create ticket":
            self._create()
        elif choice == "Read ticket details":
            self._view()
        elif choice == "Update ticket status":
            self._update()
        elif choice == "Delete ticket":
            self._delete()

    # Create flow
    def _create(self) -> None:
        st.subheader("Create New IT Ticket")

        with st.form("create_ticket_form"):
            d = st.date_input("Date")
            cat = st.text_input("Category")
            subj = st.text_input("Subject")
            pri = st.selectbox("Priority", ["Low", "Medium", "High", "Critical"])
            stat = st.selectbox("Status", ["Open", "In Progress", "Resolved", "Closed"])
            assignee = st.text_input("Assigned to (optional)")
            desc = st.text_area("Description")
            ok = st.form_submit_button("Create ticket")

        if ok and cat and subj:
            self.repo.create(
                created_date=d.strftime("%Y-%m-%d"),
                category=cat,
                subject=subj,
                priority=pri,
                status=stat,
                description=desc,
                assigned_to=assignee or None,
            )
            st.success("Ticket created successfully.")
            st.rerun()

    # Read-only ticket view
    def _view(self) -> None:
        if self.df.empty:
            st.info("No tickets available.")
            return

        opts = TicketOptions.list(self.df, "{ticket_id} | {subject}")
        sel = st.selectbox("Select ticket", opts)
        tid = sel.split("|")[0].strip()
        row = self.df[self.df["ticket_id"] == tid].iloc[0]

        st.json(row.to_dict())

    # Update status flow
    def _update(self) -> None:
        if self.df.empty:
            st.info("No tickets available.")
            return

        opts = TicketOptions.list(self.df, "{ticket_id} | {status}")
        sel = st.selectbox("Select ticket", opts)
        tid = sel.split("|")[0].strip()

        statuses = ["Open", "In Progress", "Resolved", "Closed"]
        new = st.selectbox("New status", statuses)

        if st.button("Update"):
            self.repo.update_status(tid, new)
            st.success(f"Ticket {tid} updated.")
            st.rerun()

    # Delete flow with confirmation
    def _delete(self) -> None:
        if self.df.empty:
            st.info("No tickets available.")
            return

        opts = TicketOptions.list(self.df, "{id} | {ticket_id}")
        sel = st.selectbox("Select ticket", opts)
        row_id = int(sel.split("|")[0].strip())

        if st.button("Delete ticket"):
            self.repo.delete_by_row_id(row_id)
            st.success("Ticket deleted.")
            st.rerun()
