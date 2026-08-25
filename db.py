import json
import os
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(os.environ.get("OMR_DB_PATH", Path(__file__).parent / "data" / "omr.db"))


def _connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    with _connection() as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS answer_keys (set_name TEXT PRIMARY KEY, answers TEXT NOT NULL, uploaded_at TEXT NOT NULL)")
        connection.execute("""CREATE TABLE IF NOT EXISTS student_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT, student_name TEXT NOT NULL, roll_no TEXT NOT NULL,
            set_name TEXT NOT NULL, answers TEXT NOT NULL, score INTEGER NOT NULL,
            passed INTEGER NOT NULL, evaluated_at TEXT NOT NULL, comment TEXT NOT NULL DEFAULT '')""")
        columns = {row[1] for row in connection.execute("PRAGMA table_info(student_results)")}
        if "comment" not in columns:
            connection.execute("ALTER TABLE student_results ADD COLUMN comment TEXT NOT NULL DEFAULT ''")
        connection.execute("""DELETE FROM student_results
            WHERE trim(roll_no) <> ''
              AND id NOT IN (SELECT MAX(id) FROM student_results WHERE trim(roll_no) <> '' GROUP BY roll_no)""")
        connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_student_results_roll_no ON student_results(roll_no) WHERE trim(roll_no) <> ''")


def save_answer_key(set_name: str, answers: dict[int, str], uploaded_at: str) -> None:
    init_db()
    with _connection() as connection:
        connection.execute("INSERT OR REPLACE INTO answer_keys VALUES (?, ?, ?)", (set_name, json.dumps(answers), uploaded_at))


def delete_answer_key(set_name: str) -> bool:
    """Delete one answer key only; student results are never modified."""
    init_db()
    with _connection() as connection:
        cursor = connection.execute("DELETE FROM answer_keys WHERE set_name = ?", (set_name,))
    return cursor.rowcount > 0


def delete_all_answer_keys() -> int:
    """Delete all answer keys only; student results are never modified."""
    init_db()
    with _connection() as connection:
        key_count = connection.execute("SELECT COUNT(*) FROM answer_keys").fetchone()[0]
        connection.execute("DELETE FROM answer_keys")
    return key_count


def delete_all_student_results() -> int:
    """Delete all student results only; answer keys are never modified."""
    init_db()
    with _connection() as connection:
        result_count = connection.execute("SELECT COUNT(*) FROM student_results").fetchone()[0]
        connection.execute("DELETE FROM student_results")
    return result_count


def get_answer_key(set_name: str) -> dict[int, str] | None:
    init_db()
    with _connection() as connection:
        row = connection.execute("SELECT answers FROM answer_keys WHERE set_name = ?", (set_name,)).fetchone()
    return {int(key): value for key, value in json.loads(row[0]).items()} if row else None


def get_answer_key_info(set_name: str) -> dict[str, object] | None:
    """Return a key and its upload timestamp for management displays."""
    init_db()
    with _connection() as connection:
        row = connection.execute("SELECT answers, uploaded_at FROM answer_keys WHERE set_name = ?", (set_name,)).fetchone()
    if not row:
        return None
    return {"answers": {int(key): value for key, value in json.loads(row[0]).items()}, "uploaded_at": row[1]}


def save_student_result(result) -> None:
    init_db()
    with _connection() as connection:
        values = (result.student_name, result.roll_no, result.set_name, json.dumps(result.answers), result.score, int(result.passed), result.evaluated_at, result.comment)
        if result.roll_no.strip():
            existing = connection.execute("SELECT id FROM student_results WHERE roll_no = ?", (result.roll_no,)).fetchone()
            if existing:
                connection.execute("UPDATE student_results SET student_name = ?, roll_no = ?, set_name = ?, answers = ?, score = ?, passed = ?, evaluated_at = ?, comment = ? WHERE id = ?", (*values, existing[0]))
                return
        connection.execute("INSERT INTO student_results (student_name, roll_no, set_name, answers, score, passed, evaluated_at, comment) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", values)


def get_all_results() -> pd.DataFrame:
    init_db()
    with _connection() as connection:
        return pd.read_sql_query("SELECT id, student_name, roll_no, set_name, score, passed, evaluated_at, comment FROM student_results ORDER BY id DESC", connection)


