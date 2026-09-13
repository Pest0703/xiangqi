from xiangqi_tutor.board import Position
from xiangqi_tutor.models.core import Move
from xiangqi_tutor.notation import move_to_chinese


def test_common_red_notation() -> None:
    position = Position.initial()
    assert move_to_chinese(position, Move.from_engine("h2e2")) == "炮二平五"
    assert move_to_chinese(position, Move.from_engine("h0g2")) == "马二进三"
    assert move_to_chinese(position, Move.from_engine("i0h0")) == "车一平二"
    assert move_to_chinese(position, Move.from_engine("c3c4")) == "兵七进一"


def test_black_notation_uses_black_perspective() -> None:
    position = Position.from_fen("rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR b - - 0 1")
    assert move_to_chinese(position, Move.from_engine("h7e7")) == "炮8平5"
    assert move_to_chinese(position, Move.from_engine("h9g7")) == "马8进7"
