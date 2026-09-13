from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import uuid4

from PySide6.QtCore import QObject, Signal

from xiangqi_tutor.board import IllegalMoveError
from xiangqi_tutor.models.core import Move, Side
from xiangqi_tutor.services.game import GameService, GameStatus


class GameMode(StrEnum):
    HUMAN_VS_ENGINE = "human_vs_engine"
    HUMAN_VS_HUMAN = "human_vs_human"
    ANALYSIS = "analysis"


class MatchState(StrEnum):
    WAITING_FOR_HUMAN = "waiting_for_human"
    ENGINE_THINKING = "engine_thinking"
    ANALYZING = "analyzing"
    GAME_OVER = "game_over"


class EngineStrength(StrEnum):
    CASUAL = "casual"
    STANDARD = "standard"
    STRONG = "strong"
    MAXIMUM = "maximum"

    @property
    def limits(self) -> tuple[int, int]:
        return {
            EngineStrength.CASUAL: (6, 300),
            EngineStrength.STANDARD: (10, 800),
            EngineStrength.STRONG: (14, 1800),
            EngineStrength.MAXIMUM: (18, 3500),
        }[self]


@dataclass(frozen=True, slots=True)
class EngineMoveRequest:
    request_id: str
    fen: str
    position_version: int
    depth: int
    movetime_ms: int


class MatchService(QObject):
    state_changed = Signal(object)
    engine_move_requested = Signal(object)
    engine_request_cancelled = Signal(str)
    engine_error = Signal(str)

    def __init__(self, game: GameService | None = None) -> None:
        super().__init__()
        self.game = game or GameService()
        self.mode = GameMode.HUMAN_VS_HUMAN
        self.human_side = Side.RED
        self.strength = EngineStrength.STANDARD
        self.state = MatchState.WAITING_FOR_HUMAN
        self.position_version = 0
        self._pending: EngineMoveRequest | None = None
        self.game.position_changed.connect(self._position_changed)

    @property
    def engine_side(self) -> Side | None:
        return self.human_side.opponent if self.mode is GameMode.HUMAN_VS_ENGINE else None

    @property
    def can_human_move(self) -> bool:
        if self.state is MatchState.GAME_OVER:
            return False
        if self.mode is not GameMode.HUMAN_VS_ENGINE:
            return True
        return self.state is MatchState.WAITING_FOR_HUMAN and self.game.position.side_to_move is self.human_side

    def new_match(self, mode: GameMode, human_side: Side = Side.RED, strength: EngineStrength = EngineStrength.STANDARD) -> None:
        self.cancel_engine_request()
        self.mode, self.human_side, self.strength = mode, human_side, strength
        self.game.new_game()
        self._advance_turn()

    def _position_changed(self, _position) -> None:
        self.position_version += 1
        if self.game.status in (GameStatus.CHECKMATE, GameStatus.NO_LEGAL_MOVE):
            self._set_state(MatchState.GAME_OVER)

    def _set_state(self, state: MatchState) -> None:
        self.state = state
        self.state_changed.emit(state)

    def _advance_turn(self) -> None:
        if self.game.status in (GameStatus.CHECKMATE, GameStatus.NO_LEGAL_MOVE):
            self._set_state(MatchState.GAME_OVER)
        elif self.mode is GameMode.HUMAN_VS_ENGINE and self.game.position.side_to_move is self.engine_side:
            depth, movetime = self.strength.limits
            request = EngineMoveRequest(str(uuid4()), self.game.export_fen(), self.position_version, depth, movetime)
            self._pending = request
            self._set_state(MatchState.ENGINE_THINKING)
            self.engine_move_requested.emit(request)
        else:
            self._set_state(MatchState.WAITING_FOR_HUMAN)

    def make_human_move(self, move: Move) -> None:
        if not self.can_human_move:
            raise IllegalMoveError("现在不能走棋，请等待电脑完成思考")
        self.game.move(move)
        self._advance_turn()

    def apply_engine_move(self, request_id: str, fen: str, position_version: int, move_text: str) -> bool:
        pending = self._pending
        if not pending or request_id != pending.request_id or fen != self.game.export_fen() or position_version != self.position_version:
            return False
        try:
            move = Move.from_engine(move_text)
            if move not in self.game.position.legal_moves_from(move.source):
                raise IllegalMoveError("Pikafish返回了非法走法")
            self._pending = None
            self.game.move(move)
            self._advance_turn()
            return True
        except (ValueError, IllegalMoveError) as exc:
            self._pending = None
            self._set_state(MatchState.WAITING_FOR_HUMAN)
            self.engine_error.emit(str(exc))
            return False

    def engine_failed(self, request_id: str, message: str) -> None:
        if self._pending and self._pending.request_id == request_id:
            self._pending = None
            self._set_state(MatchState.WAITING_FOR_HUMAN)
            self.engine_error.emit(message)

    def cancel_engine_request(self) -> None:
        if self._pending:
            request_id = self._pending.request_id
            self._pending = None
            self.engine_request_cancelled.emit(request_id)

    def undo_decision(self) -> bool:
        was_thinking = self.state is MatchState.ENGINE_THINKING
        self.cancel_engine_request()
        count = 1 if self.mode is not GameMode.HUMAN_VS_ENGINE or was_thinking else 2
        changed = False
        for _ in range(count):
            changed = self.game.undo() or changed
        self._advance_turn()
        return changed

    def redo_decision(self) -> bool:
        self.cancel_engine_request()
        count = 2 if self.mode is GameMode.HUMAN_VS_ENGINE else 1
        changed = False
        for _ in range(count):
            changed = self.game.redo() or changed
        self._advance_turn()
        return changed
