from dataclasses import dataclass, field
from datetime import datetime, timezone


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AnswerKey:
    set_name: str
    answers: dict[int, str]
    uploaded_at: str = field(default_factory=now_utc)


@dataclass
class StudentResult:
    student_name: str
    roll_no: str
    set_name: str
    answers: dict[int, str]
    score: int
    total: int = 50
    passed: bool = False
    evaluated_at: str = field(default_factory=now_utc)
    comment: str = ""