import pandas as pd
from app.data.db import connect_database


def get_all_tickets():
    """
    READ: Return all IT tickets from the it_tickets table.
    """
    conn = connect_database()
    df = pd.read_sql_query(
        "SELECT * FROM it_tickets ORDER BY id DESC",
        conn
    )
    conn.close()
    return df


def _generate_next_ticket_id(conn) -> str:
    """
    Generate the next ticket_id in the form TCK-00001, TCK-00002, ...
    """
    cursor = conn.cursor()
    cursor.execute("SELECT ticket_id FROM it_tickets ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()

    if row is None or row[0] is None:
        next_number = 1
    else:
        last_id = row[0]  
        try:
            number_part = int(last_id.split("-")[-1])
        except (ValueError, IndexError):
            number_part = 0
        next_number = number_part + 1

    return f"TCK-{next_number:05d}"


def create_ticket(
    created_date: str,
    category: str,
    subject: str,
    priority: str,
    status: str,
    description: str,
    assigned_to: str | None = None,
):
    """
    CREATE: Insert a new IT ticket and return the new ticket ID (e.g. TCK-00008).
    """
    conn = connect_database()
    cursor = conn.cursor()

    ticket_id = _generate_next_ticket_id(conn)

    cursor.execute(
        """
        INSERT INTO it_tickets
        (ticket_id, created_date, category, subject, priority, status, description, assigned_to)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (ticket_id, created_date, category, subject, priority, status, description, assigned_to),
    )

    conn.commit()
    conn.close()
    return ticket_id


# Alias for your Streamlit page
insert_ticket = create_ticket


def update_ticket_status(ticket_id, new_status):
    """
    UPDATE: Update the status of an existing IT ticket.
    """
    conn = connect_database()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE it_tickets
        SET status = ?
        WHERE ticket_id = ?
        """,
        (new_status, ticket_id),
    )

    conn.commit()
    conn.close()


def delete_ticket(ticket_id: int) -> int:
    """
    DELETE: Remove a ticket by its primary key ID (id column).
    Returns the number of rows deleted.
    """
    conn = connect_database()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM it_tickets WHERE id = ?", (ticket_id,))
    deleted_rows = cursor.rowcount
    conn.commit()

    conn.close()
    return deleted_rows
