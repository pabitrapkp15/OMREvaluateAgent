"""Run parser calibration against the supplied real PDF samples.

Run from the project root with: python tests/calibration_check.py
"""

import sys
import json
from pathlib import Path
from pprint import pformat

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
SAMPLES_DIR = PROJECT_ROOT / "tests" / "samples"

from pdf_parser import debug_extract, extract_answers  # noqa: E402
from evaluator import evaluate  # noqa: E402

EXPECTED_QUESTIONS = set(range(1, 51))
SETS = ["A", "B", "C", "D"]


def duplicate_questions(warnings: list[str]) -> list[str]:
    return [warning for warning in warnings if "Duplicate answer" in warning]


def inspect_sample(label: str, pdf_path: Path) -> tuple[dict[int, str], list[str]] | None:
    print(f"\n{'=' * 80}\nFILE: {label}\nPATH: {pdf_path}\n{'=' * 80}")
    if not pdf_path.is_file():
        print("STATUS: SAMPLE FILE NOT FOUND")
        print("No extraction was attempted. Place the PDF at the path above and rerun this script.")
        return None

    try:
        answers, warnings = extract_answers(pdf_path)
    except Exception as exc:
        print(f"STATUS: EXTRACTION ERROR: {exc}")
        print("FULL DEBUG DUMP:")
        print(pformat(debug_extract(pdf_path), sort_dicts=False))
        return None

    question_numbers = sorted(answers)
    missing = sorted(EXPECTED_QUESTIONS - set(answers))
    out_of_range = sorted(set(answers) - EXPECTED_QUESTIONS)
    duplicates = duplicate_questions(warnings)
    incomplete = set(question_numbers) != EXPECTED_QUESTIONS or bool(duplicates) or bool(out_of_range) or bool(warnings)

    print(f"EXTRACTED COUNT: {len(answers)}")
    print(f"QUESTION NUMBERS: {question_numbers}")
    print(f"MISSING QUESTIONS: {missing}")
    print(f"DUPLICATE WARNINGS: {duplicates}")
    print(f"OUT-OF-RANGE QUESTIONS: {out_of_range}")
    print(f"WARNINGS: {warnings}")
    print(f"EXTRACTED ANSWERS: {pformat(dict(sorted(answers.items())), sort_dicts=False)}")

    if label.startswith("master_key_set_"):
        invalid_answers = {number: answer for number, answer in answers.items() if answer not in {"A", "B", "C", "D"}}
        print(f"MASTER KEY EXACTLY 1-50: {set(answers) == EXPECTED_QUESTIONS}")
        print(f"MASTER KEY INVALID LETTERS: {invalid_answers}")

    if incomplete:
        print("STATUS: INCOMPLETE OR ANOMALOUS; FULL DEBUG DUMP FOLLOWS")
        debug = debug_extract(pdf_path)
        print("RAW EXTRACTED TEXT:")
        print(debug["raw_text"])
        print("RAW FORM-FIELD DUMP:")
        print(pformat(debug["raw_form_fields"], sort_dicts=False))
        print("PARSER CHANGE REQUIRED: inspect the raw output above to identify the exact unmatched format before changing the regex or extraction logic.")
    else:
        print("STATUS: CLEAN 50-question extraction")
    return answers, warnings


def compare_students() -> None:
    expected_path = SAMPLES_DIR / "expected_results.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    print("\nCOMPARISON TABLE")
    print("set | student | intended score | actual score | intended pass/fail | actual pass/fail | result")
    all_match = True
    master_answers_by_set = {}
    for set_name in SETS:
        master_result = inspect_sample(f"master_key_set_{set_name}", SAMPLES_DIR / f"master_key_set_{set_name}.pdf")
        if master_result is not None:
            master_answers_by_set[set_name] = master_result[0]
    for filename, details in expected.items():
        path = SAMPLES_DIR / filename
        parsed = inspect_sample(filename, path)
        if parsed is None:
            all_match = False
            print(f"{details['set']} | {details['student']} | {details['intended_score']}/50 | ERROR | {'PASS' if details['intended_passed'] else 'FAIL'} | ERROR | MISMATCH")
            continue
        answers, _ = parsed
        outcome = evaluate(answers, master_answers_by_set[details["set"]])
        actual_score = outcome["total_score"]
        actual_passed = outcome["passed"]
        match = actual_score == details["intended_score"] and actual_passed == details["intended_passed"]
        all_match = all_match and match
        print(f"{details['set']} | {details['student']} | {details['intended_score']}/50 | {actual_score}/50 | {'PASS' if details['intended_passed'] else 'FAIL'} | {'PASS' if actual_passed else 'FAIL'} | {'MATCH' if match else 'MISMATCH'}")
    print(f"\nEND-TO-END VERDICT: {'MATCH' if all_match else 'MISMATCH'}")


if __name__ == "__main__":
    compare_students()