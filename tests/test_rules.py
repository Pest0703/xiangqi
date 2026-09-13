import pytest

from xiangqi_tutor.board import START_FEN, IllegalMoveError, Piece, PieceType, Position
from xiangqi_tutor.models.core import Move, Side, Square


def sq(value: str) -> Square:
    return Square.from_engine(value)


def mv(value: str) -> Move:
    return Move.from_engine(value)


def piece(side: Side, kind: PieceType) -> Piece:
    return Piece(side, kind)


def base(side: Side = Side.RED) -> Position:
    return (
        Position.empty(side)
        .with_piece(sq("e0"), piece(Side.RED, PieceType.GENERAL))
        .with_piece(sq("d9"), piece(Side.BLACK, PieceType.GENERAL))
    )


def targets(position: Position, source: str) -> set[str]:
    return {move.target.engine for move in position.legal_moves_from(sq(source))}


def test_initial_position_and_fen_round_trip() -> None:
    position = Position.initial()
    assert sum(1 for _ in position.pieces()) == 32
    assert position.to_fen() == START_FEN
    assert len(position.legal_moves()) == 44
    assert position.piece_at(sq("a0")) == piece(Side.RED, PieceType.ROOK)
    assert position.piece_at(sq("a9")) == piece(Side.BLACK, PieceType.ROOK)


def test_rook_lines_stop_at_blockers_and_capture() -> None:
    p = base().with_piece(sq("a0"), piece(Side.RED, PieceType.ROOK))
    p = p.with_piece(sq("a2"), piece(Side.RED, PieceType.PAWN)).with_piece(sq("c0"), piece(Side.BLACK, PieceType.PAWN))
    assert targets(p, "a0") == {"a1", "b0", "c0"}


def test_horse_leg_blocks_two_moves() -> None:
    p = base().with_piece(sq("b0"), piece(Side.RED, PieceType.HORSE))
    assert {"a2", "c2", "d1"}.issubset(targets(p, "b0"))
    p = p.with_piece(sq("b1"), piece(Side.RED, PieceType.PAWN))
    assert "a2" not in targets(p, "b0") and "c2" not in targets(p, "b0")
    assert "d1" in targets(p, "b0")


def test_elephant_eye_and_river() -> None:
    p = base().with_piece(sq("c0"), piece(Side.RED, PieceType.ELEPHANT))
    assert targets(p, "c0") == {"a2", "e2"}
    p = p.with_piece(sq("d1"), piece(Side.RED, PieceType.PAWN))
    assert "e2" not in targets(p, "c0")
    p2 = base().with_piece(sq("c4"), piece(Side.RED, PieceType.ELEPHANT))
    assert all(int(target[1]) <= 4 for target in targets(p2, "c4"))


def test_advisor_and_general_stay_in_palace() -> None:
    p = base().with_piece(sq("e1"), piece(Side.RED, PieceType.ADVISOR))
    assert targets(p, "e1") == {"d0", "f0", "d2", "f2"}
    assert targets(p, "e0") <= {"d0", "f0", "e1"}


def test_cannon_moves_without_screen_and_captures_over_exactly_one() -> None:
    p = base().with_piece(sq("b2"), piece(Side.RED, PieceType.CANNON))
    p = p.with_piece(sq("b4"), piece(Side.RED, PieceType.PAWN)).with_piece(sq("b7"), piece(Side.BLACK, PieceType.ROOK))
    ts = targets(p, "b2")
    assert "b3" in ts and "b4" not in ts and "b5" not in ts and "b7" in ts
    p = p.with_piece(sq("b6"), piece(Side.RED, PieceType.PAWN))
    assert "b7" not in targets(p, "b2")


def test_pawn_before_and_after_river_never_retreats() -> None:
    p = base().with_piece(sq("c3"), piece(Side.RED, PieceType.PAWN))
    assert targets(p, "c3") == {"c4"}
    p = base().with_piece(sq("c5"), piece(Side.RED, PieceType.PAWN))
    assert targets(p, "c5") == {"b5", "d5", "c6"}
    p = (
        Position.empty(Side.BLACK)
        .with_piece(sq("e0"), piece(Side.RED, PieceType.GENERAL))
        .with_piece(sq("d9"), piece(Side.BLACK, PieceType.GENERAL))
        .with_piece(sq("c4"), piece(Side.BLACK, PieceType.PAWN))
    )
    assert targets(p, "c4") == {"b4", "d4", "c3"}


def test_generals_may_not_face_and_move_must_answer_check() -> None:
    p = (
        Position.empty()
        .with_piece(sq("e0"), piece(Side.RED, PieceType.GENERAL))
        .with_piece(sq("e9"), piece(Side.BLACK, PieceType.GENERAL))
        .with_piece(sq("e5"), piece(Side.RED, PieceType.ROOK))
    )
    assert "d5" not in targets(p, "e5")
    checked = base().with_piece(sq("e7"), piece(Side.BLACK, PieceType.ROOK)).with_piece(sq("a0"), piece(Side.RED, PieceType.ROOK))
    assert checked.is_in_check(Side.RED)
    assert checked.legal_moves_from(sq("a0")) == ()
    assert targets(checked, "e0") == {"f0"}  # d0会与黑将照面


def test_pinned_piece_cannot_expose_general() -> None:
    p = base().with_piece(sq("e7"), piece(Side.BLACK, PieceType.ROOK)).with_piece(sq("e1"), piece(Side.RED, PieceType.ROOK))
    assert "d1" not in targets(p, "e1")
    assert "e7" in targets(p, "e1")


def test_capture_and_illegal_move_rejection() -> None:
    p = base().with_piece(sq("a0"), piece(Side.RED, PieceType.ROOK)).with_piece(sq("a2"), piece(Side.BLACK, PieceType.PAWN))
    after = p.apply_move(mv("a0a2"))
    assert after.piece_at(sq("a2")) == piece(Side.RED, PieceType.ROOK)
    assert after.piece_at(sq("a0")) is None and after.side_to_move is Side.BLACK
    with pytest.raises(IllegalMoveError):
        p.apply_move(mv("a0b1"))


def test_general_is_not_captured_and_checkmate_has_no_legal_moves() -> None:
    p = (
        Position.empty(Side.BLACK)
        .with_piece(sq("e0"), piece(Side.RED, PieceType.GENERAL))
        .with_piece(sq("e9"), piece(Side.BLACK, PieceType.GENERAL))
    )
    p = (
        p.with_piece(sq("e8"), piece(Side.RED, PieceType.ROOK))
        .with_piece(sq("d8"), piece(Side.RED, PieceType.ROOK))
        .with_piece(sq("f8"), piece(Side.RED, PieceType.ROOK))
    )
    assert p.is_in_check(Side.BLACK)
    assert p.is_checkmate and p.is_game_over
    assert all(move.target != sq("e9") for move in p._apply_unchecked(mv("e8e7")).legal_moves())


def test_fen_requires_one_general_per_side_and_valid_clocks() -> None:
    with pytest.raises(ValueError, match="红方帅"):
        Position.from_fen("4k4/9/9/9/9/9/9/9/9/3K1K3 w - - 0 1")
    with pytest.raises(ValueError, match="半回合"):
        Position.from_fen(START_FEN.rsplit(" ", 2)[0] + " -1 1")
    with pytest.raises(ValueError, match="回合数"):
        Position.from_fen(START_FEN.rsplit(" ", 1)[0] + " 0")


def test_strict_fen_rejects_obviously_illegal_positions() -> None:
    facing = "4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1"
    assert Position.from_fen(facing)
    with pytest.raises(ValueError, match="照面"):
        Position.from_fen(facing, strict=True)
    outside = "4k4/9/9/9/9/9/9/9/9/K8 w - - 0 1"
    with pytest.raises(ValueError, match="九宫"):
        Position.from_fen(outside, strict=True)
