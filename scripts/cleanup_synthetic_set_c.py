"""Safely remove the unexpected synthetic Set C answer key after confirmation.

Dry run: python scripts/cleanup_synthetic_set_c.py
Delete:  python scripts/cleanup_synthetic_set_c.py --confirm
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tests"))
from generate_samples import MASTER_KEYS  # noqa: E402

DB_PATH = PROJECT_ROOT / "data" / "omr.db"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", action="store_true", help="Delete Set C only if its full mapping matches the known synthetic key")
    args = parser.parse_args()
    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute("SELECT answers FROM answer_keys WHERE set_name = 'C'").fetchone()
        if row is None:
            print("Set C is already absent; nothing to remove.")
            return
        actual = json.loads(row[0])
        expected = {str(number): answer for number, answer in MASTER_KEYS["C"].items()}
        if actual != expected:
            raise SystemExit("Refusing to delete Set C: its stored mapping does not exactly match the known synthetic key.")
        if not args.confirm:
            print("Set C matches the known synthetic key. No changes made.")
            print("Run with --confirm only after reviewing this finding.")
            return
        connection.execute("DELETE FROM answer_keys WHERE set_name = 'C'")
        print("Deleted only the confirmed synthetic Set C answer key.")


if __name__ == "__main__":
    main()