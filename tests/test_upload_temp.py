from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from app import parse_uploaded


def test_parse_uploaded_closes_windows_safe_temp_file_before_parsing():
    sample_path = Path(__file__).parent / "samples" / "master_key_set_A.pdf"
    uploaded_file = SimpleNamespace(getbuffer=lambda: memoryview(BytesIO(sample_path.read_bytes()).getvalue()))

    answers, warnings = parse_uploaded(uploaded_file)

    assert len(answers) == 50
    assert set(answers) == set(range(1, 51))
    assert warnings == []