from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT / "DATA"
DB_PATH = DATA_DIR / "intelligence_platform.db"


def connect_database():
    """Connect to the shared Week 8 database."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)
