from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from PySide6.QtCore import QObject, Signal

from xiangqi_tutor.board import Position
from xiangqi_tutor.models.core import Move, Side, Square
from xiangqi_tutor.notation import move_to_chinese
from xiangqi_tutor.services.repetition import RepetitionAdjudicator


@dataclass(frozen=True, slots=True)
class MoveRecord:
    move: Move
    chinese: str
    fen_before: str
    fen_after: str


class GameStatus(StrEnum):
    ONGOING = "ongoing"
    CHECK = "check"
    CHECKMATE = "checkmate"
    NO_LEGAL_MOVE = "no_legal_move"


class GameService(QObject):
    position_changed = Signal(object)
    move_made = Signal(object)
    game_over = Signal(str)
    status_changed = Signal(object)
    repetition_detected = Signal(str)

    def __init__(self, position: Position | None = None) -> None:
        super().__init__()
        self._position = position or Position.initial()
        self._history: list[tuple[Position, MoveRecord]] = []
        self._redo: list[tuple[MoveRecord, Position]] = []
        self._status = GameStatus.ONGOING
        self._repetition = RepetitionAdjudicator()
        self.update_game_status(emit=False)

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

    @property
    def status(self) -> GameStatus:
        return self._status

    def update_game_status(self, *, emit: bool = True) -> GameStatus:
        if self._position.is_checkmate:
            status = GameStatus.CHECKMATE
        elif self._position.is_game_over:
            status = GameStatus.NO_LEGAL_MOVE
        elif self._position.is_in_check(self._position.side_to_move):
            status = GameStatus.CHECK
        else:
            status = GameStatus.ONGOING
        self._status = status
        if emit:
            self.status_changed.emit(status)
        return status

    def _publish_position(self) -> None:
        status = self.update_game_status()
        self.position_changed.emit(self._position)
        sequence = [entry[0].to_fen() for entry in self._history] + [self._position.to_fen()]
        if self._repetition.repeated(sequence):
            self.repetition_detected.emit("检测到重复局面，正式长将/长捉判罚规则尚未启用。")
        if status in (GameStatus.CHECKMATE, GameStatus.NO_LEGAL_MOVE):
            winner = "红方" if self._position.side_to_move is Side.BLACK else "黑方"
            suffix = "将死" if status is GameStatus.CHECKMATE else "无合法着"
            self.game_over.emit(f"{winner}胜（{suffix}）")

    def new_game(self) -> None:
        self.load_fen(Position.initial().to_fen())

    def load_fen(self, fen: str) -> None:
        self._position = Position.from_fen(fen)
        self._history.clear()
        self._redo.clear()
        self._publish_position()

    def export_fen(self) -> str:
        return self._position.to_fen()

    def legal_targets(self, source: Square) -> tuple[Square, ...]:
        return tuple(move.target for move in self._position.legal_moves_from(source))

    def move(self, move: Move) -> MoveRecord:
        if self._status in (GameStatus.CHECKMATE, GameStatus.NO_LEGAL_MOVE):
            raise ValueError("对局已经结束，不能继续走棋")
        before = self._position
        after = before.apply_move(move)
        record = MoveRecord(move, move_to_chinese(before, move), before.to_fen(), after.to_fen())
        self._history.append((before, record))
        self._redo.clear()
        self._position = after
        self.move_made.emit(record)
        self._publish_position()
        return record

    def undo(self) -> bool:
        if not self._history:
            return False
        previous, record = self._history.pop()
        self._redo.append((record, self._position))
        self._position = previous
        self._publish_position()
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        record, position = self._redo.pop()
        before = self._position
        self._history.append((before, record))
        self._position = position
        self.move_made.emit(record)
        self._publish_position()
        return True
