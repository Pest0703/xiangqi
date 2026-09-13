from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CandidateMove:
    move: str
    score_cp: int | None
    mate: int | None
    depth: int
    nodes: int
    pv: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    fen: str
    best_move: str | None
    depth: int
    nodes: int
    candidates: tuple[CandidateMove, ...] = field(default_factory=tuple)

