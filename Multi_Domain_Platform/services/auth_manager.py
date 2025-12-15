from typing import Optional, Tuple  # Optional return types + simple (bool, message) validation returns
import re  # regex for username rules
import sqlite3  # raised by SQLite on UNIQUE constraint, etc.

import bcrypt  # secure password hashing (slow on purpose)

from models.user import User  # small user object used by the app
from services.database_manager import DatabaseManager  # DB wrapper used across the project


# Validate usernames in one place so login/register behave the same way
def validate_username(username: str) -> Tuple[bool, str]:
    username = username.strip()  # trim spaces users often add by accident
    if not username:
        return False, "Username cannot be empty."
    # Only letters/numbers, length 3–20 (keeps storage + UI simple)
    if not re.fullmatch(r"[A-Za-z0-9]{3,20}", username):
        return False, "Username must be 3–20 alphanumeric characters only."
    return True, ""  # empty message means "all good"


# Basic password rules (you can tighten this later if you want)
def validate_password(password: str) -> Tuple[bool, str]:
    if len(password) < 6:  # short passwords are too easy to guess
        return False, "Password must be at least 6 characters long."
    if len(password) > 50:  # avoids silly-long inputs and UI issues
        return False, "Password must be at most 50 characters long."
    return True, ""


# Small wrapper so the rest of the app doesn't deal with bcrypt details
class BcryptHasher:
    """Password hashing using bcrypt."""

    @staticmethod
    def hash_password(plain_text_password: str) -> str:
        # bcrypt works on bytes, not Python strings
        password_bytes = plain_text_password.encode("utf-8")
        # salt includes the cost factor; gensalt() chooses a safe default
        salt = bcrypt.gensalt()
        # hashpw returns bytes, which we store as a UTF-8 string in SQLite
        hashed_password = bcrypt.hashpw(password_bytes, salt)
        return hashed_password.decode("utf-8")

    @staticmethod
    def check_password(plain_text_password: str, hashed_password: str) -> bool:
        # Compare user input with stored hash (bcrypt handles the salt internally)
        return bcrypt.checkpw(
            plain_text_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )


# Main auth service used by your Streamlit login/register page
class AuthManager:
    """Handles user registration and login against the SQLite users table."""

    def __init__(self, db: DatabaseManager):
        self._db = db  # keep one DB manager instance around

    def register_user(self, username: str, password: str, role: str = "user") -> None:
        """
        Register a new user.
        Raises ValueError for validation issues and sqlite3.IntegrityError
        if the username already exists (UNIQUE constraint).
        """
        # Validate username early so we fail fast with a friendly message
        ok, msg = validate_username(username)
        if not ok:
            raise ValueError(msg)

        # Validate password rules (simple length checks for now)
        ok, msg = validate_password(password)
        if not ok:
            raise ValueError(msg)

        # Store a bcrypt hash, never the plain password
        password_hash = BcryptHasher.hash_password(password)

        # Insert user record (username is UNIQUE in your schema)
        self._db.execute_query(
            """
            INSERT INTO users (username, password_hash, role)
            VALUES (?, ?, ?)
            """,
            (username, password_hash, role),
        )

    def login_user(self, username: str, password: str) -> Optional[User]:
        """
        Attempt to log in a user.
        Returns a User object if successful, otherwise None.
        """
        # Fetch the stored hash + role for this username
        row = self._db.fetch_one(
            """
            SELECT username, password_hash, role
            FROM users
            WHERE username = ?
            """,
            (username,),
        )

        # No record means wrong username (or not registered yet)
        if row is None:
            return None

        # Unpack DB row values
        username_db, password_hash_db, role_db = row

        # Verify password and return a User object on success
        if BcryptHasher.check_password(password, password_hash_db):
            return User(username_db, password_hash_db, role_db)

        # Password didn't match
        return None
