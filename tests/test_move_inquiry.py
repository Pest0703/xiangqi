from xiangqi_tutor.board import Piece, PieceType, Position
from xiangqi_tutor.models.core import Move, Side, Square
from xiangqi_tutor.services import MoveInquiryService


def test_inquiry_distinguishes_basic_rule_and_exposing_general() -> None:
    service = MoveInquiryService()
    initial = Position.initial()
    blocked_rook = service.inspect(initial, Move.from_engine("a0a3"))
    assert not blocked_rook.legal and "路径" in blocked_rook.rule_explanation

    position = (
        Position.empty(Side.RED)
        .with_piece(Square.from_engine("e0"), Piece(Side.RED, PieceType.GENERAL))
        .with_piece(Square.from_engine("d9"), Piece(Side.BLACK, PieceType.GENERAL))
        .with_piece(Square.from_engine("e7"), Piece(Side.BLACK, PieceType.ROOK))
        .with_piece(Square.from_engine("e1"), Piece(Side.RED, PieceType.ROOK))
    )
    exposed = service.inspect(position, Move.from_engine("e1d1"))
    assert not exposed.legal and "将帅" in exposed.rule_explanation


def test_inquiry_says_legal_move_can_be_assessed_separately() -> None:
    result = MoveInquiryService().inspect(Position.initial(), Move.from_engine("h2e2"))
    assert result.legal and result.rule_explanation is None
