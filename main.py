from pathlib import Path
import pandas as pd

from app.data.db import connect_database, DB_PATH
from app.data.schema import create_all_tables
from app.services.user_service import register_user, login_user, migrate_users_from_file
from app.data.incidents import (
    insert_incident,
    get_all_incidents,
    get_incidents_by_type_count,
    get_high_severity_by_status,
    get_incident_types_with_many_cases,
    update_incident_status,
    delete_incident,
)
from app.data.datasets import load_csv_to_table


def main():
    print("=" * 60)
    print("Week 8: Database Demo")
    print("=" * 60)

    # 1. Setup database
    conn = connect_database()
    create_all_tables(conn)
    conn.close()

    # 2. Migrate users
    migrate_users_from_file()

    # 3. Verify migrated users
    conn = connect_database()
    cursor = conn.cursor()

    cursor.execute("SELECT id, username, role FROM users")
    users = cursor.fetchall()

    print("\nUsers in database:")
    print(f"{'ID':<5} {'Username':<15} {'Role':<10}")
    print("-" * 35)
    for user in users:
        print(f"{user[0]:<5} {user[1]:<15} {user[2]:<10}")

    print(f"\nTotal users: {len(users)}")
    conn.close()

    # 4. Test authentication
    success, msg = register_user("alice", "SecurePass123!", "analyst")
    print(msg)

    success, msg = login_user("alice", "SecurePass123!")
    print(msg)

    # 5. Test Incident CRUD
    incident_id = insert_incident(
        "2024-11-05",
        "Phishing",
        "High",
        "Open",
        "Suspicious email detected",
        "alice",
    )
    print(f"Created incident #{incident_id}")

    # 6. Query incidents
    df = get_all_incidents()
    print(f"Total incidents: {len(df)}")


def setup_database_complete():
    """
    Complete database setup.
    """
    print("\n" + "=" * 60)
    print("STARTING COMPLETE DATABASE SETUP")
    print("=" * 60)

    conn = connect_database()

    # Step 1: Create tables
    create_all_tables(conn)
    print("[1/4] Tables created")

    # Step 2: Migrate users
    migrated = migrate_users_from_file()
    print(f"[2/4] Migrated {migrated} users")

    # Step 3: Load CSV data
    print("[3/4] Loading CSV files...")
    load_csv_to_table("DATA/cyber_incidents.csv", "cyber_incidents")
    load_csv_to_table("DATA/datasets_metadata.csv", "datasets_metadata")
    load_csv_to_table("DATA/it_tickets.csv", "it_tickets")

    # Step 4: Verify table counts
    cursor = conn.cursor()
    tables = ["users", "cyber_incidents", "datasets_metadata", "it_tickets"]

    print("\nDatabase Summary:")
    print(f"{'Table':<25} {'Rows':<10}")
    print("-" * 40)

    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"{table:<25} {count:<10}")

    conn.close()
    print("\nDATABASE SETUP COMPLETE!")


def run_comprehensive_tests():
    """
    Run comprehensive tests on your database.
    """
    print("\n" + "=" * 60)
    print("🧪 RUNNING COMPREHENSIVE TESTS")
    print("=" * 60)

    conn = connect_database()

    # Test 1: Authentication
    print("\n[TEST 1] Authentication")
    success, msg = register_user("test_user", "TestPass123!", "user")
    print(f"  Register: {'✅' if success else '❌'} {msg}")

    success, msg = login_user("test_user", "TestPass123!")
    print(f"  Login:    {'✅' if success else '❌'} {msg}")

    # Test 2: CRUD Operations
    print("\n[TEST 2] CRUD Operations")

    # Create
    test_id = insert_incident(
        "2024-11-05",
        "Test Incident",
        "Low",
        "Open",
        "This is a test incident",
        "test_user"
    )
    print(f"  Create: Incident #{test_id} created")

    # Read
    df = pd.read_sql_query(
        "SELECT * FROM cyber_incidents WHERE id = ?",
        conn,
        params=(test_id,)
    )
    print(f"  Read:   Found incident #{test_id}")

    # Update
    update_incident_status(test_id, "Resolved")
    print("  Update: Status updated")

    # Delete
    delete_incident(test_id)
    print("  Delete: Incident deleted")

    # Test 3: Analytical Queries
    print("\n[TEST 3] Analytical Queries")

    df_by_type = get_incidents_by_type_count(conn)
    print(f"  By Type: {len(df_by_type)} types")

    df_high = get_high_severity_by_status(conn)
    print(f"  High Severity: {len(df_high)} statuses")

    conn.close()

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)



if __name__ == "__main__":
    main()                   # Week 8 demo
    run_comprehensive_tests()  # Full testing suite
    setup_database_complete()

