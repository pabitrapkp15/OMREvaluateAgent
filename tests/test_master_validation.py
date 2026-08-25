from app import is_complete_master_key


def test_master_key_validation_remains_strict():
    incomplete_answers = {number: "A" for number in range(1, 46)}
    wrong_number_answers = {number: "A" for number in range(1, 50)} | {51: "A"}
    assert not is_complete_master_key(incomplete_answers)
    assert not is_complete_master_key(wrong_number_answers)
    assert is_complete_master_key({number: "A" for number in range(1, 51)})