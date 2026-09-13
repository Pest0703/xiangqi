from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True, slots=True)
class EvidencePiece:
    square: str
    side: str
    piece: str


@dataclass(frozen=True, slots=True)
class EvidenceCandidate:
    move: str
    chinese: str
    score_for_red: int | None
    depth: int
    pv: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TutorEvidence:
    fen: str
    side_to_move: str
    pieces: tuple[EvidencePiece, ...]
    legal_moves: tuple[str, ...]
    recent_moves: tuple[str, ...] = ()
    last_move: str | None = None
    played_move: str | None = None
    best_move: str | None = None
    candidate_moves: tuple[EvidenceCandidate, ...] = ()
    score_before: int | None = None
    score_after: int | None = None
    score_for_red: int | None = None
    pv: tuple[str, ...] = ()
    branch_id: str = "main"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
