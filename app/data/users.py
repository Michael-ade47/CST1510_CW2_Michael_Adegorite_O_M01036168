from app.data.db import connect_database


import bcrypt
from .db import connect_database


def verify_user(username: str, plain_password: str) -> bool:
    
    conn = connect_database()
    cur = conn.cursor()

    cur.execute(
        "SELECT password_hash FROM users WHERE username = ?",
        (username,),
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        
        return False

    stored_hash = row[0] 

    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        stored_hash.encode("utf-8"),
    )


def get_user_role(username: str) -> str | None:
    conn = connect_database()
    cur = conn.cursor()

    cur.execute(
        "SELECT role FROM users WHERE username = ?",
        (username,),
    )
    row = cur.fetchone()
    conn.close()

    return row[0] if row else None


def get_user_by_username(username: str):
    """Retrieve a single user row by username, or None."""
    conn = connect_database()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    )
    user = cursor.fetchone()
    conn.close()
    return user


def insert_user(username: str, password_hash: str, role: str = "user"):
    """Insert a new user into the users table."""
    conn = connect_database()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, password_hash, role)
    )
    conn.commit()
    conn.close()
