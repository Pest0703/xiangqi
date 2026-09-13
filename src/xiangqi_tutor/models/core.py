from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Side(StrEnum):
    RED = "w"
    BLACK = "b"

    @property
    def opponent(self) -> "Side":
        return Side.BLACK if self is Side.RED else Side.RED


@dataclass(frozen=True, slots=True)
class Square:
    file: int
    rank: int

    def __post_init__(self) -> None:
        if not 0 <= self.file < 9 or not 0 <= self.rank < 10:
            raise ValueError("象棋坐标必须位于九路十行内")

    @property
    def engine(self) -> str:
        return f"{chr(ord('a') + self.file)}{self.rank}"

    @classmethod
    def from_engine(cls, value: str) -> "Square":
        if len(value) != 2 or value[0] not in "abcdefghi" or value[1] not in "0123456789":
            raise ValueError(f"无效引擎坐标：{value}")
        return cls(ord(value[0]) - ord("a"), int(value[1]))


@dataclass(frozen=True, slots=True)
class Move:
    source: Square
    target: Square

    @property
    def engine(self) -> str:
        return self.source.engine + self.target.engine

    @classmethod
    def from_engine(cls, value: str) -> "Move":
        if len(value) != 4:
            raise ValueError(f"无效引擎走法：{value}")
        return cls(Square.from_engine(value[:2]), Square.from_engine(value[2:]))
