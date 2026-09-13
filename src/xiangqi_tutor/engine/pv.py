from __future__ import annotations

from dataclasses import dataclass

from xiangqi_tutor.board import Position
from xiangqi_tutor.models.core import Move, Side
from xiangqi_tutor.notation import move_to_chinese


@dataclass(frozen=True, slots=True)
class ValidatedPVStep:
    move: str
    chinese: str
    fen_before: str
    fen_after: str
    side: Side


class PVValidator:
    @staticmethod
    def validate(position: Position, pv: tuple[str, ...]) -> tuple[ValidatedPVStep, ...]:
        current = position
        result: list[ValidatedPVStep] = []
        for raw in pv:
            try:
                move = Move.from_engine(raw)
                if move not in current.legal_moves_from(move.source):
                    break
                chinese = move_to_chinese(current, move)
                before = current.to_fen()
                side = current.side_to_move
                current = current.apply_move(move)
                result.append(ValidatedPVStep(raw, chinese, before, current.to_fen(), side))
            except (ValueError, TypeError):
                break
        return tuple(result)
