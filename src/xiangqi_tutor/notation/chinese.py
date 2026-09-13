from __future__ import annotations

from xiangqi_tutor.board.position import PieceType, Position
from xiangqi_tutor.models.core import Move, Side

RED_NUMBERS = "一二三四五六七八九"
NAMES = {
    (Side.RED, PieceType.GENERAL): "帅",
    (Side.BLACK, PieceType.GENERAL): "将",
    (Side.RED, PieceType.ADVISOR): "仕",
    (Side.BLACK, PieceType.ADVISOR): "士",
    (Side.RED, PieceType.ELEPHANT): "相",
    (Side.BLACK, PieceType.ELEPHANT): "象",
    (Side.RED, PieceType.HORSE): "马",
    (Side.BLACK, PieceType.HORSE): "马",
    (Side.RED, PieceType.ROOK): "车",
    (Side.BLACK, PieceType.ROOK): "车",
    (Side.RED, PieceType.CANNON): "炮",
    (Side.BLACK, PieceType.CANNON): "炮",
    (Side.RED, PieceType.PAWN): "兵",
    (Side.BLACK, PieceType.PAWN): "卒",
}


def file_number(side: Side, file: int) -> str:
    number = 9 - file if side is Side.RED else file + 1
    return RED_NUMBERS[number - 1] if side is Side.RED else str(number)


def move_to_chinese(position: Position, move: Move) -> str:
    piece = position.piece_at(move.source)
    if piece is None:
        raise ValueError("走法起点没有棋子")
    same_file = sorted(
        (square for square, other in position.pieces() if other == piece and square.file == move.source.file),
        key=lambda square: square.rank,
        reverse=piece.side is Side.RED,
    )
    if len(same_file) == 2 and piece.kind in (PieceType.ROOK, PieceType.CANNON, PieceType.HORSE, PieceType.PAWN):
        prefix = ("前" if move.source == same_file[0] else "后") + NAMES[(piece.side, piece.kind)]
    else:
        prefix = NAMES[(piece.side, piece.kind)] + file_number(piece.side, move.source.file)
    dr = move.target.rank - move.source.rank
    if dr == 0:
        action, suffix = "平", file_number(piece.side, move.target.file)
    else:
        action = "进" if ((dr > 0) == (piece.side is Side.RED)) else "退"
        if piece.kind in (PieceType.HORSE, PieceType.ELEPHANT, PieceType.ADVISOR):
            suffix = file_number(piece.side, move.target.file)
        else:
            distance = abs(dr)
            suffix = RED_NUMBERS[distance - 1] if piece.side is Side.RED else str(distance)
    return prefix + action + suffix
