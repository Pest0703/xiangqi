from __future__ import annotations

from collections import Counter


class RepetitionAdjudicator:
    """只检测重复，不擅自套用国际象棋和棋规则。"""

    @staticmethod
    def position_key(fen: str) -> str:
        parts = fen.split()
        if len(parts) < 2:
            raise ValueError("无效FEN")
        return " ".join(parts[:2])

    def repeated(self, fens: list[str] | tuple[str, ...], *, occurrences: int = 3) -> bool:
        counts = Counter(self.position_key(fen) for fen in fens)
        return any(count >= occurrences for count in counts.values())
