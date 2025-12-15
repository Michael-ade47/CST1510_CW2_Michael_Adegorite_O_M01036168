import sqlite3
from pathlib import Path
from typing import Any, Iterable, Optional


class DatabaseManager:
    """Handles SQLite database connections and queries."""

    def __init__(self, db_path: str):
        # Store the path to the SQLite database file
        self._db_path = db_path
        # Hold a single reusable connection
        self._connection: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        # Open a database connection if one does not already exist
        if self._connection is None:
            # Ensure the database directory exists
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

            # Create the SQLite connection
            self._connection = sqlite3.connect(
                self._db_path,
                check_same_thread=False,  # Allow use across Streamlit reruns/threads
                timeout=30,               # Wait up to 30s if the DB is locked
            )
            # Return rows as dictionary-like objects
            self._connection.row_factory = sqlite3.Row

    def init_schema(self) -> None:
        """Create required tables if they don't exist."""
        # Initialise the users table for authentication
        self.execute_query(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL
            );
            """
        )

    def close(self) -> None:
        # Cleanly close the database connection
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def execute_query(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        """Execute a write query (INSERT, UPDATE, DELETE)."""
        # Ensure a connection exists
        if self._connection is None:
            self.connect()
        # Run the query and commit changes
        cur = self._connection.cursor()
        cur.execute(sql, tuple(params))
        self._connection.commit()
        return cur

    def fetch_one(self, sql: str, params: Iterable[Any] = ()):
        # Fetch a single row from the database
        if self._connection is None:
            self.connect()
        cur = self._connection.cursor()
        cur.execute(sql, tuple(params))
        return cur.fetchone()

    def fetch_all(self, sql: str, params: Iterable[Any] = ()):
        # Fetch all matching rows from the database
        if self._connection is None:
            self.connect()
        cur = self._connection.cursor()
        cur.execute(sql, tuple(params))
        return cur.fetchall()
