from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ScoreKind(StrEnum):
    CP = "cp"
    MATE = "mate"


@dataclass(frozen=True, slots=True)
class EvalScore:
    kind: ScoreKind
    value: int
    pov: str = "side_to_move"
    score_for_red: int | None = None

    def for_red_text(self) -> str:
        if self.kind is ScoreKind.CP:
            return f"{(self.score_for_red or 0) / 100:+.2f}"
        winner = "红方" if (self.score_for_red or 0) > 0 else "黑方"
        return f"{winner}{abs(self.value)}步杀"


@dataclass(frozen=True, slots=True)
class CandidateMove:
    move: str
    score_cp: int | None
    mate: int | None
    depth: int
    nodes: int
    pv: tuple[str, ...] = ()
    score_for_red: int | None = None
    evaluation: EvalScore | None = None


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    fen: str
    side_to_move: str
    best_move: str | None
    depth: int
    nodes: int
    time_ms: int = 0
    score_raw: int | None = None
    score_pov: str = "side_to_move"
    score_for_red: int | None = None
    candidates: tuple[CandidateMove, ...] = field(default_factory=tuple)
