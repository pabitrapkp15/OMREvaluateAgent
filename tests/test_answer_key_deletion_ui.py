from pathlib import Path

from streamlit.testing.v1 import AppTest

from db import delete_all_answer_keys, delete_all_student_results, get_all_results, get_answer_key, save_answer_key, save_student_result
from models import StudentResult


APP_PATH = str(Path(__file__).parents[1] / "app.py")
KEY = {number: "A" for number in range(1, 51)}


def open_app():
    return AppTest.from_file(APP_PATH).run()


def test_per_set_delete_cancel_leaves_key_and_results_untouched():
    delete_all_answer_keys()
    delete_all_student_results()
    save_answer_key("A", KEY, "test")
    save_answer_key("B", KEY, "test")
    save_student_result(StudentResult("Student", "001", "A", {1: "A"}, 1))

    app = open_app()
    app.button(key="delete_key_A").click()
    app.run()
    assert any(button.label == "Confirm" for button in app.button)
    app.button(key="cancel_delete_set").click()
    app.run()

    assert get_answer_key("A") == KEY
    assert get_answer_key("B") == KEY
    assert len(get_all_results()) == 1


def test_per_set_delete_confirm_removes_only_selected_key():
    delete_all_answer_keys()
    delete_all_student_results()
    save_answer_key("A", KEY, "test")
    save_answer_key("B", KEY, "test")
    save_student_result(StudentResult("Student", "001", "A", {1: "A"}, 1))

    app = open_app()
    app.button(key="delete_key_A").click()
    app.run()
    assert any(button.key == "confirm_delete_set" for button in app.button)
    assert any("Delete the saved answer key for Set A?" in item.value for item in app.markdown)


def test_delete_all_confirm_removes_keys_but_preserves_results():
    delete_all_answer_keys()
    delete_all_student_results()
    save_answer_key("A", KEY, "test")
    save_answer_key("B", KEY, "test")
    save_student_result(StudentResult("Student", "001", "A", {1: "A"}, 1))

    app = open_app()
    app.button(key="delete_all_keys").click()
    app.run()
    assert any(button.key == "confirm_delete_all" for button in app.button)
    assert any("Delete ALL saved answer keys for Sets A, B?" in item.value for item in app.markdown)


def test_delete_all_cancel_preserves_keys_and_results():
    delete_all_answer_keys()
    delete_all_student_results()
    save_answer_key("A", KEY, "test")
    save_student_result(StudentResult("Student", "001", "A", {1: "A"}, 1))

    app = open_app()
    app.button(key="delete_all_keys").click()
    app.run()
    app.button(key="cancel_delete_all").click()
    app.run()

    assert get_answer_key("A") == KEY
    assert len(get_all_results()) == 1


def test_clear_student_results_opens_separate_confirmation():
    delete_all_answer_keys()
    delete_all_student_results()
    save_answer_key("A", KEY, "test")
    save_student_result(StudentResult("Student", "001", "A", {1: "A"}, 1))

    app = open_app()
    app.button(key="clear_all_student_results").click()
    app.run()

    assert any(button.key == "confirm_clear_results" for button in app.button)
    assert any("Answer keys will not be changed" in item.value for item in app.markdown)
    app.button(key="cancel_clear_results").click()
    app.run()
    assert get_answer_key("A") == KEY
    assert len(get_all_results()) == 1
