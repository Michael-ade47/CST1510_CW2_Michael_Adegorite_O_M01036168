from pathlib import Path
import re
import bcrypt

USER_DATA_FILE = Path("users.txt")


def hash_password(plain_text_password: str) -> str:
    password_bytes = plain_text_password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    return hashed_password.decode("utf-8")


def verify_password(plain_text_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_text_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def validate_username(username: str) -> tuple[bool, str]:
    username = username.strip()
    if not username:
        return False, "Username cannot be empty."
    if not re.fullmatch(r"[A-Za-z0-9]{3,20}", username):
        return False, "Username must be 3–20 alphanumeric characters only."
    return True, ""


def validate_password(password: str) -> tuple[bool, str]:
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
    if len(password) > 50:
        return False, "Password must be at most 50 characters long."
    return True, ""


def user_exists(username: str) -> bool:
    if not USER_DATA_FILE.exists():
        return False

    with USER_DATA_FILE.open(mode="r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "," not in line:
                continue
            saved_username, _ = line.split(",", 1)
            if saved_username == username:
                return True
    return False


def register_user(username: str, password: str) -> tuple[bool, str]:
    ok, msg = validate_username(username)
    if not ok:
        return False, msg

    ok, msg = validate_password(password)
    if not ok:
        return False, msg

    if user_exists(username):
        return False, f"Username '{username}' already exists."

    hashed_password = hash_password(password)

    with USER_DATA_FILE.open(mode="a", encoding="utf-8", newline="") as f:
        f.write(f"{username},{hashed_password}\n")

    return True, f"User '{username}' registered successfully."


def login_user(username: str, password: str) -> tuple[bool, str]:
    if not USER_DATA_FILE.exists():
        return False, "No users are registered yet."

    with USER_DATA_FILE.open(mode="r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "," not in line:
                continue

            saved_username, saved_hash = line.split(",", 1)

            if saved_username == username:
                if verify_password(password, saved_hash):
                    return True, f"Welcome, {username}!"
                else:
                    return False, "Incorrect password."

    return False, f"Username '{username}' was not found."
.