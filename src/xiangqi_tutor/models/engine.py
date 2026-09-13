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
    score_for_red: int | None = None


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
