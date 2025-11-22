import pandas as pd
from pathlib import Path
from app.data.db import connect_database


def load_csv_to_table(csv_path, table_name):
    """
    Load a CSV file into a database table using pandas.

    Args:
        csv_path: Path to CSV file
        table_name: Name of the target table
        
    Returns:
        int: Number of rows loaded into the table
    """
    csv_path = Path(csv_path)

    # Check CSV exists
    if not csv_path.exists():
        print(f" CSV file not found: {csv_path}")
        return 0

    # Read CSV
    df = pd.read_csv(csv_path)

    # Connect to database
    conn = connect_database()

    # Load data
    df.to_sql(
        name=table_name,
        con=conn,
        if_exists="append",
        index=False
    )

    row_count = len(df)

    conn.close()

    print(f" Loaded {row_count} rows from '{csv_path.name}' into '{table_name}'")
    return row_count
