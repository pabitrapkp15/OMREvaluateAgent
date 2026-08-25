import json
from pathlib import Path

from batch import evaluate_batch, parse_batch_filename
from db import clear_all_data, get_all_results, save_answer_key, save_student_result
from pdf_parser import extract_answers


SAMPLES = Path(__file__).parent / "samples"


def test_roll_numbered_samples_parse_and_save_as_distinct_batch_rows():
    clear_all_data()
    expected = json.loads((SAMPLES / "expected_results.json").read_text(encoding="utf-8"))
    new_files = [name for name, details in expected.items() if "roll_no" in details]
    for set_name in "ABCD":
        answers, warnings = extract_answers(SAMPLES / f"master_key_set_{set_name}.pdf")
        assert warnings == []
        save_answer_key(set_name, answers, "sample-test")
    file_pairs = [(name, str(SAMPLES / name)) for name in new_files]
    rows = evaluate_batch(file_pairs, "A", {set_name: extract_answers(SAMPLES / f"master_key_set_{set_name}.pdf")[0] for set_name in "ABCD"}, extract_answers, save_student_result)
    assert len(rows) == 20
    assert all(row["status"] == "success" for row in rows)
    assert {parse_batch_filename(name)["roll_no"] for name in new_files} == {f"{number:03d}" for number in range(7, 27)}
    saved = get_all_results()
    assert len(saved) == 20
    assert set(saved["roll_no"]) == {f"{number:03d}" for number in range(7, 27)}
