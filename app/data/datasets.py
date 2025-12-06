import pandas as pd
from app.data.db import connect_database

def create_dataset(**fields) -> int:
    """
    CREATE: Insert a new row into datasets_metadata.

    Usage:
        create_dataset(name="Users CSV", source="users.csv", rows=1000)
    Returns:
        int: ID of the newly inserted dataset.
    """
    if not fields:
        raise ValueError("No fields provided to create_dataset")

    columns = ", ".join(fields.keys())
    placeholders = ", ".join(["?"] * len(fields))
    values = list(fields.values())

    conn = connect_database()
    cursor = conn.cursor()
    cursor.execute(
        f"INSERT INTO datasets_metadata ({columns}) VALUES ({placeholders})",
        values,
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def read_all_datasets() -> pd.DataFrame:
    """
    READ: Return all rows from datasets_metadata as a DataFrame.
    """
    conn = connect_database()
    df = pd.read_sql_query(
        "SELECT * FROM datasets_metadata ORDER BY id DESC",
        conn
    )
    conn.close()
    return df


def update_dataset(dataset_id: int, **fields) -> int:
    """
    UPDATE: Update one dataset row by ID.

    Usage:
        update_dataset(3, rows=1200, description="Updated row count")

    Returns:
        int: Number of rows updated (0 or 1).
    """
    if not fields:
        raise ValueError("No fields provided to update_dataset")

    set_clause = ", ".join([f"{col} = ?" for col in fields.keys()])
    values = list(fields.values())
    values.append(dataset_id)

    conn = connect_database()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE datasets_metadata SET {set_clause} WHERE id = ?",
        values,
    )
    conn.commit()
    rows_updated = cursor.rowcount
    conn.close()
    return rows_updated


def delete_dataset(dataset_id: int) -> int:
    """
    DELETE: Delete one dataset row by ID.

    Returns:
        int: Number of rows deleted (0 or 1).
    """
    conn = connect_database()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM datasets_metadata WHERE id = ?",
        (dataset_id,),
    )
    conn.commit()
    rows_deleted = cursor.rowcount
    conn.close()
    return rows_deleted
