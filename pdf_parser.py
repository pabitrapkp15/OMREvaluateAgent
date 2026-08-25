"""Extract OMR answers from AcroForm PDFs or typed PDF text."""

import re
from pathlib import Path
from typing import Any

import pdfplumber
from pypdf import PdfReader

QUESTION_PATTERN = re.compile(r"(?:^|\bQ(?:uestion)?\s*)?(\d{1,2})\s*(?:[.):\-]|\s)\s*([ABCD])\b", re.IGNORECASE)
FIELD_PATTERN = re.compile(r"(?:q(?:uestion)?[_\-\s]?)?(\d{1,2})$", re.IGNORECASE)


def _normalise_answer(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("/V", value.get("/AS"))
    if value is None:
        return None
    answer = str(value).strip().lstrip("/").upper()
    return answer if answer in {"A", "B", "C", "D"} else None


def _extract_form_fields(pdf_path: str | Path) -> tuple[dict[int, str], list[str], dict[str, Any]]:
    reader = PdfReader(str(pdf_path))
    fields = reader.get_fields() or {}
    answers: dict[int, str] = {}
    warnings: list[str] = []
    raw_fields: dict[str, Any] = {}
    for name, field in fields.items():
        raw_fields[str(name)] = field
        match = FIELD_PATTERN.search(str(name).strip().replace("/", ""))
        if not match:
            continue
        question_number = int(match.group(1))
        answer = _normalise_answer(field)
        if answer is None:
            warnings.append(f"Question {question_number} has a blank or invalid form value")
            continue
        if question_number in answers:
            warnings.append(f"Duplicate answer for question {question_number} in form fields")
        answers[question_number] = answer
    return answers, warnings, raw_fields


def _extract_text(pdf_path: str | Path) -> tuple[str, dict[int, str], list[str]]:
    chunks: list[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text() or "")
    raw_text = "\n".join(chunks)
    answers: dict[int, str] = {}
    warnings: list[str] = []
    for match in QUESTION_PATTERN.finditer(raw_text):
        question_number = int(match.group(1))
        answer = match.group(2).upper()
        if not 1 <= question_number <= 50:
            warnings.append(f"Question number {question_number} is outside 1-50")
            continue
        if question_number in answers:
            warnings.append(f"Duplicate answer for question {question_number}")
        answers[question_number] = answer
    missing = sorted(set(range(1, 51)) - set(answers))
    if missing:
        warnings.append("Missing question numbers: " + ", ".join(map(str, missing)))
    return raw_text, answers, warnings


def extract_answers(pdf_path: str | Path) -> tuple[dict[int, str], list[str]]:
    """Return ``(answers, warnings)`` for a PDF, preferring clean AcroForm data."""
    try:
        form_answers, form_warnings, _ = _extract_form_fields(pdf_path)
        if set(form_answers) == set(range(1, 51)) and not form_warnings:
            return form_answers, []
    except Exception as exc:
        form_answers, form_warnings = {}, [f"Form extraction unavailable: {exc}"]

    _, text_answers, text_warnings = _extract_text(pdf_path)
    warnings = form_warnings + text_warnings if "form_warnings" in locals() else text_warnings
    return text_answers, warnings


def debug_extract(pdf_path: str | Path) -> dict[str, Any]:
    """Return raw text and a serialisable dump of raw AcroForm fields."""
    try:
        _, _, raw_fields = _extract_form_fields(pdf_path)
    except Exception as exc:
        raw_fields = {"_error": str(exc)}
    try:
        raw_text, _, _ = _extract_text(pdf_path)
    except Exception as exc:
        raw_text = f"[Text extraction error] {exc}"
    return {"raw_text": raw_text, "raw_form_fields": raw_fields}