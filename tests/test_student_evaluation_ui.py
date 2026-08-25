from pathlib import Path

from streamlit.testing.v1 import AppTest

from db import save_answer_key
from pdf_parser import extract_answers


def test_student_evaluation_keeps_inputs_until_manual_reset():
    sample_path = Path(__file__).parent / "samples" / "student_topper_set_A.pdf"
    app_path = Path(__file__).parents[1] / "app.py"
    master_answers, warnings = extract_answers(Path(__file__).parent / "samples" / "master_key_set_A.pdf")
    assert warnings == []
    save_answer_key("A", master_answers, "test-upload")

    app = AppTest.from_file(app_path).run()
    name = next(item for item in app.text_input if item.label == "Student name")
    roll = next(item for item in app.text_input if item.label == "Roll number")
    name.set_value("Test Student")
    roll.set_value("ROLL-001")
    student_uploader = next(item for item in app.file_uploader if item.label == "Upload student answer PDF")
    student_uploader.upload(sample_path.name, sample_path.read_bytes())
    app.run()
    next(item for item in app.button if item.label == "Evaluate").click()
    app.run()

    name = next(item for item in app.text_input if item.label == "Student name")
    roll = next(item for item in app.text_input if item.label == "Roll number")
    assert name.value == "Test Student"
    assert roll.value == "ROLL-001"
    assert next(item for item in app.selectbox if item.label == "Exam set").value == "A"
    student_uploader = next(item for item in app.file_uploader if item.label == "Upload student answer PDF")
    assert student_uploader.value is not None
    assert any("48/50" in item.value for item in app.markdown)
    assert any("PASS" in item.value for item in app.markdown)
    next(item for item in app.button if item.label == "Reset for next student").click()
    app.run()
    assert next(item for item in app.text_input if item.label == "Student name").value == ""
    assert next(item for item in app.text_input if item.label == "Roll number").value == ""
    assert next(item for item in app.selectbox if item.label == "Exam set").value == "A"
    assert next(item for item in app.file_uploader if item.label == "Upload student answer PDF").value is None
    assert not any("48/50" in item.value for item in app.markdown)