import sqlite3
from pathlib import Path

import bcrypt

from app.data.db import connect_database

DATA_DIR = Path("DATA")


def register_user(username, password, role="user"):
    """
    Register a new user in the database.

    Args:
        username: User's login name
        password: Plain text password (will be hashed)
        role: User role (default: 'user')

    Returns:
        tuple: (success: bool, message: str)
    """
    conn = connect_database()
    cursor = conn.cursor()

    # Check if user already exists
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return False, f"Username '{username}' already exists."

    # Hash the password
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    password_hash = hashed.decode("utf-8")

    # Insert new user
    cursor.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, password_hash, role),
    )
    conn.commit()
    conn.close()

    return True, f"User '{username}' registered successfully!"


import bcrypt
from app.data.db import connect_database

def login_user(username, password):
    """
    Authenticate a user against the database.

    Args:
        username: User's login name
        password: Plain text password to verify

    Returns:
        tuple: (success: bool, message: str)
    """
    conn = connect_database()
    cursor = conn.cursor()
    
    # Find user
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return False, "Username not found."
    
    # Verify password (user[2] is password_hash column)
    stored_hash = user[2]   # (id, username, password_hash, role)
    password_bytes = password.encode('utf-8')
    hash_bytes = stored_hash.encode('utf-8')
    
    if bcrypt.checkpw(password_bytes, hash_bytes):
        return True, f"Welcome, {username}!"
    else:
        return False, "Invalid password."


def migrate_users_from_file(filepath=DATA_DIR / "users.txt"):
    """
    Migrate users from users.txt to the database.

    Expected file format per line:
        username,password_hash
    (role is set to 'user' by default)

    This function:
    - Skips empty lines
    - Skips invalid lines
    - Uses INSERT OR IGNORE so existing users are not duplicated
    """
    filepath = Path(filepath)

    if not filepath.exists():
        print(f"⚠️  File not found: {filepath}")
        print("   No users to migrate.")
        return 0

    conn = connect_database()
    cursor = conn.cursor()
    migrated_count = 0

    with filepath.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split(",")
            if len(parts) >= 2:
                username = parts[0].strip()
                password_hash = parts[1].strip()

                try:
                    cursor.execute(
                        "INSERT OR IGNORE INTO users (username, password_hash, role) "
                        "VALUES (?, ?, ?)",
                        (username, password_hash, "user"),
                    )
                    if cursor.rowcount > 0:
                        migrated_count += 1
                except sqlite3.Error as e:
                    print(f"Error migrating user {username}: {e}")

    conn.commit()
    conn.close()
    print(f"✅ Migrated {migrated_count} users from {filepath.name}")
    return migrated_count
