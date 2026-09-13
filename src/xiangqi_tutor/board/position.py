from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterator

from xiangqi_tutor.models.core import Move, Side, Square

START_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"


class PieceType(StrEnum):
    GENERAL = "k"
    ADVISOR = "a"
    ELEPHANT = "b"
    HORSE = "n"
    ROOK = "r"
    CANNON = "c"
    PAWN = "p"


@dataclass(frozen=True, slots=True)
class Piece:
    side: Side
    kind: PieceType

    @property
    def fen(self) -> str:
        value = self.kind.value
        return value.upper() if self.side is Side.RED else value


class IllegalMoveError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Position:
    """权威棋局状态。

    file 0..8 对应 Pikafish a..i；rank 0 是红方底线，rank 9 是黑方底线。
    GUI 翻转不得修改这里的坐标。board 按 rank * 9 + file 存储。
    """

    board: tuple[Piece | None, ...]
    side_to_move: Side = Side.RED
    halfmove_clock: int = 0
    fullmove_number: int = 1

    def __post_init__(self) -> None:
        if len(self.board) != 90:
            raise ValueError("棋盘必须恰好包含90个位置")

    @classmethod
    def initial(cls) -> "Position":
        return cls.from_fen(START_FEN)

    @classmethod
    def empty(cls, side_to_move: Side = Side.RED) -> "Position":
        return cls((None,) * 90, side_to_move)

    @staticmethod
    def _index(square: Square) -> int:
        return square.rank * 9 + square.file

    def piece_at(self, square: Square) -> Piece | None:
        return self.board[self._index(square)]

    def with_piece(self, square: Square, piece: Piece | None) -> "Position":
        cells = list(self.board)
        cells[self._index(square)] = piece
        return Position(tuple(cells), self.side_to_move, self.halfmove_clock, self.fullmove_number)

    def pieces(self) -> Iterator[tuple[Square, Piece]]:
        for rank in range(10):
            for file in range(9):
                square = Square(file, rank)
                piece = self.piece_at(square)
                if piece:
                    yield square, piece

    @classmethod
    def from_fen(cls, fen: str, *, strict: bool = False) -> "Position":
        parts = fen.strip().split()
        if len(parts) < 2:
            raise ValueError("FEN必须至少包含棋盘和行棋方")
        rows = parts[0].split("/")
        if len(rows) != 10:
            raise ValueError("中国象棋FEN必须包含10行")
        cells: list[Piece | None] = [None] * 90
        kinds = {kind.value: kind for kind in PieceType}
        for row_index, row in enumerate(rows):
            rank = 9 - row_index
            file = 0
            for char in row:
                if char in "123456789":
                    file += int(char)
                elif char.lower() in kinds:
                    if file >= 9:
                        raise ValueError("FEN行超出九路")
                    side = Side.RED if char.isupper() else Side.BLACK
                    cells[rank * 9 + file] = Piece(side, kinds[char.lower()])
                    file += 1
                else:
                    raise ValueError(f"FEN包含未知棋子：{char}")
            if file != 9:
                raise ValueError("FEN每行必须恰好九路")
        try:
            side = Side(parts[1])
        except ValueError as exc:
            raise ValueError("FEN行棋方必须是w或b") from exc
        try:
            halfmove = int(parts[4]) if len(parts) > 4 else 0
            fullmove = int(parts[5]) if len(parts) > 5 else 1
        except ValueError as exc:
            raise ValueError("FEN时钟字段必须是整数") from exc
        if halfmove < 0:
            raise ValueError("FEN半回合时钟不能为负数")
        if fullmove < 1:
            raise ValueError("FEN回合数必须大于等于1")
        position = cls(tuple(cells), side, halfmove, fullmove)
        position.validate(strict=strict)
        return position

    def validate(self, *, strict: bool = False) -> None:
        for side, name in ((Side.RED, "红方帅"), (Side.BLACK, "黑方将")):
            count = sum(piece.side is side and piece.kind is PieceType.GENERAL for _, piece in self.pieces())
            if count != 1:
                raise ValueError(f"FEN必须包含恰好一个{name}")
        if not strict:
            return
        for square, piece in self.pieces():
            if piece.kind in (PieceType.GENERAL, PieceType.ADVISOR) and not self._palace(piece.side, square):
                raise ValueError("严格校验失败：将帅或仕士位于九宫之外")
            if piece.kind is PieceType.ELEPHANT:
                on_own_side = square.rank <= 4 if piece.side is Side.RED else square.rank >= 5
                if not on_own_side:
                    raise ValueError("严格校验失败：相象越过河界")
        red = self.general_square(Side.RED)
        black = self.general_square(Side.BLACK)
        if red and black and red.file == black.file:
            between = range(min(red.rank, black.rank) + 1, max(red.rank, black.rank))
            if all(self.piece_at(Square(red.file, rank)) is None for rank in between):
                raise ValueError("严格校验失败：将帅照面")

    def to_fen(self) -> str:
        rows: list[str] = []
        for rank in range(9, -1, -1):
            empty = 0
            row = ""
            for file in range(9):
                piece = self.piece_at(Square(file, rank))
                if piece is None:
                    empty += 1
                else:
                    if empty:
                        row += str(empty)
                        empty = 0
                    row += piece.fen
            if empty:
                row += str(empty)
            rows.append(row)
        return f"{'/'.join(rows)} {self.side_to_move.value} - - {self.halfmove_clock} {self.fullmove_number}"

    @staticmethod
    def _inside(file: int, rank: int) -> bool:
        return 0 <= file < 9 and 0 <= rank < 10

    @staticmethod
    def _palace(side: Side, square: Square) -> bool:
        return 3 <= square.file <= 5 and ((0 <= square.rank <= 2) if side is Side.RED else (7 <= square.rank <= 9))

    def _ray(self, source: Square, df: int, dr: int) -> Iterator[Square]:
        file, rank = source.file + df, source.rank + dr
        while self._inside(file, rank):
            yield Square(file, rank)
            file += df
            rank += dr

    def pseudo_moves_from(self, source: Square, *, attacks: bool = False) -> Iterator[Move]:
        piece = self.piece_at(source)
        if piece is None:
            return
        candidates: list[Square] = []
        if piece.kind is PieceType.ROOK:
            for df, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                for target in self._ray(source, df, dr):
                    occupant = self.piece_at(target)
                    if occupant is None:
                        candidates.append(target)
                    else:
                        if occupant.side is not piece.side:
                            candidates.append(target)
                        break
        elif piece.kind is PieceType.CANNON:
            for df, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                screen = False
                for target in self._ray(source, df, dr):
                    occupant = self.piece_at(target)
                    if not screen:
                        if occupant is None:
                            if not attacks:
                                candidates.append(target)
                        else:
                            screen = True
                    elif occupant is not None:
                        if occupant.side is not piece.side:
                            candidates.append(target)
                        break
        elif piece.kind is PieceType.HORSE:
            for df, dr, lf, lr in (
                (1, 2, 0, 1),
                (-1, 2, 0, 1),
                (1, -2, 0, -1),
                (-1, -2, 0, -1),
                (2, 1, 1, 0),
                (2, -1, 1, 0),
                (-2, 1, -1, 0),
                (-2, -1, -1, 0),
            ):
                if self._inside(source.file + lf, source.rank + lr) and self.piece_at(Square(source.file + lf, source.rank + lr)) is None:
                    if self._inside(source.file + df, source.rank + dr):
                        candidates.append(Square(source.file + df, source.rank + dr))
        elif piece.kind is PieceType.ELEPHANT:
            for df, dr in ((2, 2), (-2, 2), (2, -2), (-2, -2)):
                tf, tr = source.file + df, source.rank + dr
                if self._inside(tf, tr) and ((tr <= 4) if piece.side is Side.RED else (tr >= 5)):
                    eye = Square(source.file + df // 2, source.rank + dr // 2)
                    if self.piece_at(eye) is None:
                        candidates.append(Square(tf, tr))
        elif piece.kind is PieceType.ADVISOR:
            for df, dr in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                if self._inside(source.file + df, source.rank + dr):
                    target = Square(source.file + df, source.rank + dr)
                    if self._palace(piece.side, target):
                        candidates.append(target)
        elif piece.kind is PieceType.GENERAL:
            for df, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if self._inside(source.file + df, source.rank + dr):
                    target = Square(source.file + df, source.rank + dr)
                    if self._palace(piece.side, target):
                        candidates.append(target)
            for target in self._ray(source, 0, 1 if piece.side is Side.RED else -1):
                occupant = self.piece_at(target)
                if occupant:
                    if attacks and occupant.side is not piece.side and occupant.kind is PieceType.GENERAL:
                        candidates.append(target)
                    break
        elif piece.kind is PieceType.PAWN:
            forward = 1 if piece.side is Side.RED else -1
            if self._inside(source.file, source.rank + forward):
                candidates.append(Square(source.file, source.rank + forward))
            crossed = source.rank >= 5 if piece.side is Side.RED else source.rank <= 4
            if crossed:
                for df in (-1, 1):
                    if self._inside(source.file + df, source.rank):
                        candidates.append(Square(source.file + df, source.rank))
        for target in candidates:
            if not self._inside(target.file, target.rank):
                continue
            occupant = self.piece_at(target)
            if occupant is None or occupant.side is not piece.side:
                if occupant and occupant.kind is PieceType.GENERAL and not attacks:
                    continue
                yield Move(source, target)

    def _apply_unchecked(self, move: Move) -> "Position":
        piece = self.piece_at(move.source)
        cells = list(self.board)
        cells[self._index(move.source)] = None
        cells[self._index(move.target)] = piece
        captured = self.piece_at(move.target)
        return Position(
            tuple(cells),
            self.side_to_move.opponent,
            0 if captured or (piece and piece.kind is PieceType.PAWN) else self.halfmove_clock + 1,
            self.fullmove_number + (1 if self.side_to_move is Side.BLACK else 0),
        )

    def general_square(self, side: Side) -> Square | None:
        return next((square for square, piece in self.pieces() if piece.side is side and piece.kind is PieceType.GENERAL), None)

    def is_in_check(self, side: Side) -> bool:
        general = self.general_square(side)
        if general is None:
            return True
        for square, piece in self.pieces():
            if piece.side is side.opponent:
                if any(move.target == general for move in self.pseudo_moves_from(square, attacks=True)):
                    return True
        return False

    def legal_moves_from(self, source: Square) -> tuple[Move, ...]:
        piece = self.piece_at(source)
        if piece is None or piece.side is not self.side_to_move:
            return ()
        result = []
        for move in self.pseudo_moves_from(source):
            next_position = self._apply_unchecked(move)
            if not next_position.is_in_check(piece.side):
                result.append(move)
        return tuple(result)

    def legal_moves(self) -> tuple[Move, ...]:
        return tuple(move for square, piece in self.pieces() if piece.side is self.side_to_move for move in self.legal_moves_from(square))

    def apply_move(self, move: Move) -> "Position":
        if move not in self.legal_moves_from(move.source):
            raise IllegalMoveError(f"非法走法：{move.engine}")
        return self._apply_unchecked(move)

    @property
    def is_game_over(self) -> bool:
        return not self.legal_moves()

    @property
    def is_checkmate(self) -> bool:
        return self.is_in_check(self.side_to_move) and self.is_game_over
