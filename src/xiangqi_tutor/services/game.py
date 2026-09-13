from __future__ import annotations

from dataclasses import dataclass
from PySide6.QtCore import QObject, Signal
from xiangqi_tutor.board import Position
from xiangqi_tutor.models.core import Move, Side, Square
from xiangqi_tutor.notation import move_to_chinese


@dataclass(frozen=True, slots=True)
class MoveRecord:
    move: Move
    chinese: str
    fen_before: str
    fen_after: str


class GameService(QObject):
    position_changed = Signal(object)
    move_made = Signal(object)
    game_over = Signal(str)

    def __init__(self, position: Position | None = None) -> None:
        super().__init__()
        self._position = position or Position.initial()
        self._history: list[tuple[Position, MoveRecord]] = []
        self._redo: list[tuple[MoveRecord, Position]] = []

    @property
    def position(self) -> Position:
        return self._position

    @property
    def records(self) -> tuple[MoveRecord, ...]:
        return tuple(record for _, record in self._history)

    @property
    def can_undo(self) -> bool:
        return bool(self._history)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def new_game(self) -> None:
        self.load_fen(Position.initial().to_fen())

    def load_fen(self, fen: str) -> None:
        self._position = Position.from_fen(fen)
        self._history.clear()
        self._redo.clear()
        self.position_changed.emit(self._position)

    def export_fen(self) -> str:
        return self._position.to_fen()

    def legal_targets(self, source: Square) -> tuple[Square, ...]:
        return tuple(move.target for move in self._position.legal_moves_from(source))

    def move(self, move: Move) -> MoveRecord:
        before = self._position
        after = before.apply_move(move)
        record = MoveRecord(move, move_to_chinese(before, move), before.to_fen(), after.to_fen())
        self._history.append((before, record))
        self._redo.clear()
        self._position = after
        self.move_made.emit(record)
        self.position_changed.emit(after)
        if after.is_game_over:
            winner = "红方" if after.side_to_move is Side.BLACK else "黑方"
            suffix = "将死" if after.is_checkmate else "无合法着"
            self.game_over.emit(f"{winner}胜（{suffix}）")
        return record

    def undo(self) -> bool:
        if not self._history:
            return False
        previous, record = self._history.pop()
        self._redo.append((record, self._position))
        self._position = previous
        self.position_changed.emit(previous)
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        record, position = self._redo.pop()
        before = self._position
        self._history.append((before, record))
        self._position = position
        self.move_made.emit(record)
        self.position_changed.emit(position)
        return True
