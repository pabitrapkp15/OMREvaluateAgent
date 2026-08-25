"""Safely reset the production OMR database.

Dry run: python scripts/reset_db.py
Reset:    python scripts/reset_db.py --confirm
"""

import argparse
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "omr.db"


def current_counts() -> tuple[int, int]:
    if not DB_PATH.exists():
        return 0, 0
    with sqlite3.connect(DB_PATH) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        key_count = connection.execute("SELECT COUNT(*) FROM answer_keys").fetchone()[0] if "answer_keys" in tables else 0
        result_count = connection.execute("SELECT COUNT(*) FROM student_results").fetchone()[0] if "student_results" in tables else 0
    return key_count, result_count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", action="store_true", help="Actually delete all answer keys and student results")
    args = parser.parse_args()
    key_count, result_count = current_counts()
    if not args.confirm:
        print(f"Would delete {key_count} answer keys and {result_count} student results from {DB_PATH}.")
        print("No changes made. Re-run with --confirm to reset the database.")
        return
    if not DB_PATH.exists():
        print(f"Cleared 0 answer keys and 0 student results from {DB_PATH}; database was already empty.")
        return
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS answer_keys (set_name TEXT PRIMARY KEY, answers TEXT NOT NULL, uploaded_at TEXT NOT NULL)")
        connection.execute("""CREATE TABLE IF NOT EXISTS student_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT, student_name TEXT NOT NULL, roll_no TEXT NOT NULL,
            set_name TEXT NOT NULL, answers TEXT NOT NULL, score INTEGER NOT NULL,
            passed INTEGER NOT NULL, evaluated_at TEXT NOT NULL)""")
        connection.execute("DELETE FROM answer_keys")
        connection.execute("DELETE FROM student_results")
    print(f"Cleared {key_count} answer keys and {result_count} student results from {DB_PATH}.")


if __name__ == "__main__":
    main()