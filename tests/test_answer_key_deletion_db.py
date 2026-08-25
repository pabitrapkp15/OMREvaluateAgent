from db import delete_all_answer_keys, delete_all_student_results, delete_answer_key, get_all_results, get_answer_key, save_answer_key, save_student_result
from models import StudentResult


KEY = {number: "A" for number in range(1, 51)}


def seed_results():
    save_student_result(StudentResult("Student", "001", "A", {1: "A"}, 1))


def test_delete_answer_key_leaves_other_keys_and_results():
    delete_all_answer_keys()
    delete_all_student_results()
    save_answer_key("A", KEY, "test")
    save_answer_key("B", KEY, "test")
    seed_results()

    assert delete_answer_key("A") is True
    assert get_answer_key("A") is None
    assert get_answer_key("B") == KEY
    assert len(get_all_results()) == 1


def test_delete_all_answer_keys_leaves_results_untouched():
    delete_all_answer_keys()
    delete_all_student_results()
    save_answer_key("A", KEY, "test")
    save_answer_key("B", KEY, "test")
    seed_results()

    assert delete_all_answer_keys() == 2
    assert get_answer_key("A") is None
    assert get_answer_key("B") is None
    assert len(get_all_results()) == 1
