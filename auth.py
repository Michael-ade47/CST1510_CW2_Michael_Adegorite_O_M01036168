from pathlib import Path
import bcrypt

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

USER_DATA_FILE = Path("users.txt")  

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

def register_user(username: str, password: str) -> bool:
    # Username validation
    is_valid, error_msg = validate_username(username)
    if not is_valid:
        print(f"Error: {error_msg}")
        return False

    # Password validation
    is_valid, error_msg = validate_password(password)
    if not is_valid:
        print(f"Error: {error_msg}")
        return False

    if user_exists(username):
        print(f"Error: Username '{username}' already exists.")
        return False

    hashed_password = hash_password(password)
    with USER_DATA_FILE.open(mode="a", encoding="utf-8", newline="") as f:
        f.write(f"{username},{hashed_password}\n")
    print(f"User '{username}' registered.")
    return True

def login_user(username: str, password: str) -> bool:
    if not USER_DATA_FILE.exists():
        print("No users registered yet.")
        return False

    with USER_DATA_FILE.open(mode="r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "," not in line:
                continue
            saved_username, saved_hash = line.split(",", 1)
            if saved_username == username:
                if verify_password(password, saved_hash):
                    print(f"Success: Welcome, {username}!")
                    return True
                else:
                    print("Incorrect password.")
                    return False

    print(f"Username '{username}' was not found.")
    return False

def validate_username(username: str) -> tuple[bool, str]:
    """
    Returns (is_valid, error_message)
    """
    username = username.strip()
    if not username:
        return False, "Username cannot be empty."
    if "," in username:
        return False, "Username cannot contain a comma."
    if len(username) < 3:
        return False, "Username must be at least 3 characters long."
    return True, ""

def validate_password(password: str) -> tuple[bool, str]:
    """
    Simple password policy (adjust as needed).
    Returns (is_valid, error_message).
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    # You can add more checks (digits, symbols, etc.) here if you want:
    # if not any(c.isdigit() for c in password): ...
    return True, ""

def display_menu():
    print("\n" + "=" * 50)
    print(" MULTI-DOMAIN INTELLIGENCE PLATFORM")
    print(" Secure Authentication System")
    print("=" * 50)
    print("\n[1] Register a new user")
    print("[2] Login")
    print("[3] Exit")
    print("-" * 50)

def main():
    print("\nWelcome to the Week 7 Authentication System!")
    while True:
        display_menu()
        choice = input("\nPlease select an option (1-3): ").strip()

        if choice == "1":
            # Registration flow
            print("\n--- USER REGISTRATION ---")
            username = input("Enter a username: ").strip()
            is_valid, error_msg = validate_username(username)
            if not is_valid:
                print(f"Error: {error_msg}")
                continue

            password = input("Enter a password: ").strip()
            is_valid, error_msg = validate_password(password)
            if not is_valid:
                print(f"Error: {error_msg}")
                continue

            password_confirm = input("Confirm password: ").strip()
            if password != password_confirm:
                print("Error: Passwords do not match.")
                continue

            register_user(username, password)

        elif choice == "2":
            # Login flow
            print("\n--- USER LOGIN ---")
            username = input("Enter your username: ").strip()
            password = input("Enter your password: ").strip()
            if login_user(username, password):
                print("\nYou are now logged in.")
                input("\nPress Enter to return to the main menu...")

        elif choice == "3":
            print("\nThank you for using the authentication system.")
            print("Exiting...")
            break

        else:
            print("\nError: Invalid option. Please select 1, 2, or 3.")

if __name__ == "__main__":
    main()
