from batch import evaluate_batch, parse_batch_filename
from db import clear_all_data, get_all_results, save_student_result


def key():
    return {number: "A" for number in range(1, 51)}


def test_new_filename_convention_extracts_name_roll_and_set():
    assert parse_batch_filename("Ananya_Sharma_007_SetA.pdf") == {"student_name": "Ananya Sharma", "roll_no": "007", "set_name": "A"}


def test_old_filename_convention_keeps_blank_roll():
    assert parse_batch_filename("Ananya_Sharma_SetA.pdf") == {"student_name": "Ananya Sharma", "roll_no": "", "set_name": "A"}


def test_filename_parts_are_detected_independently():
    assert parse_batch_filename("Ananya_Sharma_007.pdf") == {"student_name": "Ananya Sharma", "roll_no": "007", "set_name": ""}
    assert parse_batch_filename("Ananya_Sharma_SetA.pdf")["set_name"] == "A"


def test_batch_all_files_succeed():
    saved = []
    result = evaluate_batch([("Asha.pdf", "one.pdf"), ("Bina.pdf", "two.pdf")], "A", {"A": key()}, lambda _: (key(), []), saved.append)
    assert [row["status"] for row in result] == ["success", "success"]
    assert len(saved) == 2


def test_batch_duplicate_roll_numbers_last_file_updates_existing_result():
    clear_all_data()
    files = [("Asha_007_SetA.pdf", "first.pdf"), ("Asha_007_SetA.pdf", "second.pdf")]
    answers = key()

    def extract(path):
        return answers if path == "first.pdf" else {**answers, 1: "B"}, []

    evaluate_batch(files, "A", {"A": key()}, extract, save_student_result)
    results = get_all_results()
    assert len(results) == 1
    assert results.iloc[0]["roll_no"] == "007"
    assert results.iloc[0]["score"] == 49


def test_batch_continues_after_missing_key_and_incomplete_file():
    saved = []
    answers = key()
    files = [("Asha_SetA.pdf", "good.pdf"), ("Bina_SetB.pdf", "missing-key.pdf"), ("Chet_SetA.pdf", "incomplete.pdf"), ("Dev_SetA.pdf", "good-2.pdf")]

    def extract(path):
        if path == "incomplete.pdf":
            return {1: "A"}, ["Missing question numbers: 2-50"]
        return answers, []

    result = evaluate_batch(files, "A", {"A": key(), "B": None}, extract, saved.append)
    assert [row["status"] for row in result] == ["success", "failed: no saved answer key", "success", "success"]
    assert result[2]["comment"] == "Answer not submitted - auto-fail regardless of score"
    assert len(saved) == 3


def test_batch_marks_every_file_failed_when_selected_key_is_missing():
    saved = []
    result = evaluate_batch([("Asha_SetB.pdf", "one.pdf"), ("Bina_SetB.pdf", "two.pdf")], "B", {"B": None}, lambda _: (key(), []), saved.append)
    assert all(row["status"] == "failed: no saved answer key" for row in result)
    assert saved == []