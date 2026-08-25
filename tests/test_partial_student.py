from pathlib import Path

from evaluator import PARTIAL_SUBMISSION_COMMENT, evaluate
from pdf_parser import extract_answers


def test_partial_student_answers_score_blanks_and_receive_comment():
    path = Path(__file__).parent / "samples" / "student_partial_attempt_set_A.pdf"
    answers, warnings = extract_answers(path)
    master, master_warnings = extract_answers(Path(__file__).parent / "samples" / "master_key_set_A.pdf")
    assert len(answers) == 45
    assert master_warnings == []
    outcome = evaluate(answers, master)
    comment = outcome["comment"]
    assert outcome["total_score"] == 35
    assert outcome["passed"] is False
    assert comment == PARTIAL_SUBMISSION_COMMENT


def test_partial_submission_above_cutoff_is_still_fail():
    answers = {number: "A" for number in range(1, 46)}
    outcome = evaluate(answers, {number: "A" for number in range(1, 51)})
    assert outcome["total_score"] == 45
    assert outcome["passed"] is False
    assert outcome["partial_submission"] is True
    assert outcome["comment"] == PARTIAL_SUBMISSION_COMMENT


def test_full_submission_above_cutoff_still_passes():
    outcome = evaluate({number: "A" for number in range(1, 51)}, {number: "A" for number in range(1, 51)})
    assert outcome["total_score"] == 50
    assert outcome["passed"] is True
    assert outcome["partial_submission"] is False
    assert outcome["comment"] == ""