from evaluator import evaluate


def key():
    return {number: "A" for number in range(1, 51)}


def test_all_correct():
    result = evaluate(key(), key())
    assert result["total_score"] == 50
    assert result["passed"] is True


def test_all_wrong():
    result = evaluate({number: "B" for number in range(1, 51)}, key())
    assert result["total_score"] == 0
    assert result["passed"] is False


def test_missing_answers_are_incorrect():
    result = evaluate({1: "A"}, key())
    assert result["total_score"] == 1
    assert sum(not item["correct"] for item in result["questions"]) == 49


def test_exactly_at_cutoff_passes():
    answers = {number: "A" if number <= 40 else "B" for number in range(1, 51)}
    assert evaluate(answers, key())["passed"] is True


def test_one_below_cutoff_fails():
    answers = {number: "A" if number <= 39 else "B" for number in range(1, 51)}
    assert evaluate(answers, key())["passed"] is False


def test_unknown_question_is_anomaly():
    result = evaluate({**key(), 51: "A"}, key())
    assert result["total_score"] == 50
    assert result["anomalies"]