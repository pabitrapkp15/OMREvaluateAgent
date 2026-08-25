"""Generate additive roll-numbered batch samples without changing existing PDFs."""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = PROJECT_ROOT / "tests" / "samples"
sys.path.insert(0, str(Path(__file__).parent))

from generate_samples import MASTER_KEYS, answer_line, make_pdf  # noqa: E402

SCENARIOS = [
    ("Ananya Sharma", "topper", 2, 0, 48, True),
    ("Rohan Mehta", "boundary_pass", 10, 0, 40, True),
    ("Ishita Nair", "boundary_fail", 11, 0, 39, False),
    ("Vikram Singh", "low_scorer", 30, 0, 20, False),
    ("Meera Iyer", "partial_attempt", 10, 5, 35, False),
]


def main() -> None:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    expected_path = SAMPLES_DIR / "expected_results.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    roll_number = 7
    generated = []
    for set_name, master_key in MASTER_KEYS.items():
        for student_name, variant, wrong_count, blank_count, score, passed in SCENARIOS:
            answers = dict(master_key)
            for number in range(1, wrong_count + 1):
                answers[number] = next(option for option in "ABCD" if option != master_key[number])
            for number in range(wrong_count + 1, wrong_count + blank_count + 1):
                answers.pop(number)
            roll_no = f"{roll_number:03d}"
            filename = f"{student_name.replace(' ', '_')}_{roll_no}_Set{set_name}.pdf"
            lines = [f"Student: {student_name}", f"Set: {set_name}"] + [answer_line(number, answer) for number, answer in answers.items()]
            make_pdf(SAMPLES_DIR / filename, f"Set {set_name} Student Answer Sheet: {student_name}", lines)
            expected[filename] = {"student": student_name, "roll_no": roll_no, "set": set_name, "intended_score": score, "intended_passed": passed}
            generated.append(filename)
            roll_number += 1
    expected_path.write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(generated)} new roll-numbered PDFs")
    print("\n".join(generated))


if __name__ == "__main__":
    main()
