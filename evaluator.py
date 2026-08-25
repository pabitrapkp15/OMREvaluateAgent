TOTAL_QUESTIONS = 50
PARTIAL_SUBMISSION_COMMENT = "Answer not submitted - auto-fail regardless of score"


def evaluate(student_answers: dict[int, str], answer_key: dict[int, str], cutoff: int = 40) -> dict:
    """Score answers and reject partial submissions even when their score passes.

    A partial sheet is not a valid attempt, so its numeric score is retained for
    transparency but its pass status is explicitly forced to False.
    """
    questions = []
    anomalies = []
    score = 0
    for question_number in sorted(answer_key):
        student_answer = str(student_answers.get(question_number, "")).strip().upper()
        correct_answer = str(answer_key[question_number]).strip().upper()
        is_correct = student_answer == correct_answer and student_answer in {"A", "B", "C", "D"}
        score += int(is_correct)
        questions.append({"question_number": question_number, "student_answer": student_answer or "Blank", "correct_answer": correct_answer, "correct": is_correct})
    for question_number in sorted(set(student_answers) - set(answer_key)):
        anomalies.append(f"Student answer includes question {question_number}, which is not present in the key")
    partial_submission = len(student_answers) < TOTAL_QUESTIONS
    passed = score >= cutoff and not partial_submission
    return {
        "questions": questions,
        "total_score": score,
        "passed": passed,
        "partial_submission": partial_submission,
        "comment": PARTIAL_SUBMISSION_COMMENT if partial_submission else "",
        "anomalies": anomalies,
    }