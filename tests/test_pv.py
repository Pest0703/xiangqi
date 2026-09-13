from xiangqi_tutor.board import Position
from xiangqi_tutor.engine import PVValidator


def test_pv_validator_builds_structured_steps_and_truncates_illegal_tail() -> None:
    steps = PVValidator.validate(Position.initial(), ("h2e2", "h7e7", "a0a9", "h0g2"))
    assert [step.move for step in steps] == ["h2e2", "h7e7"]
    assert steps[0].chinese == "炮二平五"
    assert steps[0].fen_after == steps[1].fen_before
