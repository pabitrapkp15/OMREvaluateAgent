"""Batch student evaluation orchestration, independent of Streamlit."""

import re
from pathlib import Path
from typing import Callable, Iterable

from evaluator import evaluate
from models import StudentResult


def student_name_from_filename(filename: str) -> str:
    return parse_batch_filename(filename)["student_name"]


def parse_batch_filename(filename: str) -> dict[str, str]:
    """Extract student name, optional roll number, and optional set marker."""
    stem = Path(filename).stem
    set_match = re.search(r"(?:^|[_\- ]+)Set[_\- ]?([ABCD])(?:$|[_\- .])", stem, re.IGNORECASE)
    set_name = set_match.group(1).upper() if set_match else ""
    without_set = stem[:set_match.start()] + stem[set_match.end():] if set_match else stem
    roll_match = re.search(r"(?:^|[_\- ])(\d+)$", without_set)
    roll_no = roll_match.group(1) if roll_match else ""
    if roll_match:
        without_set = without_set[:roll_match.start()].rstrip("_ -")
    student_name = re.sub(r"[_\-]+", " ", without_set).strip() or "Unnamed student"
    return {"student_name": student_name, "roll_no": roll_no, "set_name": set_name}


def set_from_filename(filename: str, default_set: str) -> str:
    match = re.search(r"(?:^|[_\- ])Set[_\- ]?([ABCD])(?:[_\- .]|$)", Path(filename).name, re.IGNORECASE)
    return match.group(1).upper() if match else default_set


def evaluate_batch(
    files: Iterable[tuple[str, str]],
    default_set: str,
    answer_keys: dict[str, dict[int, str] | None],
    extract_func: Callable[[str], tuple[dict[int, str], list[str]]],
    save_func: Callable[[StudentResult], None],
) -> list[dict[str, str | int]]:
    """Evaluate all files, continuing after per-file failures.

    ``files`` contains ``(display_filename, local_path)`` pairs. The selected
    set applies to every file; successful records are persisted via save_func.
    """
    results: list[dict[str, str | int]] = []
    for filename, local_path in files:
        filename_parts = parse_batch_filename(filename)
        name = filename_parts["student_name"]
        set_name = filename_parts["set_name"] or default_set
        roll_no = filename_parts["roll_no"]
        key = answer_keys.get(set_name)
        if not key:
            results.append({"student_name": name, "set": set_name, "score": "", "result": "", "comment": "", "status": "failed: no saved answer key"})
            continue
        try:
            answers, warnings = extract_func(local_path)
            if not answers:
                reason = "no answers extracted"
                if warnings:
                    reason += "; " + "; ".join(warnings)
                results.append({"student_name": name, "set": set_name, "score": "", "result": "", "comment": "", "status": "failed: " + reason})
                continue
            outcome = evaluate(answers, key)
            comment = outcome["comment"]
            result = StudentResult(name, roll_no, set_name, answers, outcome["total_score"], passed=outcome["passed"], comment=comment)
            save_func(result)
            results.append({"student_name": name, "set": set_name, "score": f"{result.score}/50", "result": "PASS" if result.passed else "FAIL", "comment": comment, "status": "success"})
        except Exception as exc:
            results.append({"student_name": name, "set": set_name, "score": "", "result": "", "comment": "", "status": f"failed: {exc}"})
    return results