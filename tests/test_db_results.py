from db import clear_all_data, get_all_results, save_student_result
from models import StudentResult


def make_result(roll_no: str, score: int, comment: str = "") -> StudentResult:
    return StudentResult("Student", roll_no, "A", {1: "A"}, score, passed=score >= 40, comment=comment)


def test_same_nonblank_roll_number_updates_one_row():
    clear_all_data()
    save_student_result(make_result("ROLL-1", 40))
    save_student_result(make_result("ROLL-1", 48, "Answer not submitted"))
    results = get_all_results()
    assert len(results) == 1
    assert results.iloc[0]["score"] == 48
    assert results.iloc[0]["comment"] == "Answer not submitted"


def test_blank_roll_numbers_are_not_deduplicated():
    clear_all_data()
    save_student_result(make_result("", 20))
    save_student_result(make_result("", 30))
    assert len(get_all_results()) == 2