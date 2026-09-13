from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, Field

SQUARE_PATTERN = re.compile(r"^[a-i][0-9]$")


class TutorArrow(BaseModel):
    source: str
    target: str
    type: Literal["recommended", "danger", "plan"] = "recommended"


class TutorHighlight(BaseModel):
    square: str
    type: Literal["key", "danger"] = "key"


class TutorResponse(BaseModel):
    summary: str = ""
    explanation: str = ""
    recommended_moves: list[str] = Field(default_factory=list)
    variations: list[list[str]] = Field(default_factory=list)
    arrows: list[TutorArrow] = Field(default_factory=list)
    highlights: list[TutorHighlight] = Field(default_factory=list)
    key_squares: list[str] = Field(default_factory=list)
    lesson: str = ""

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "TutorResponse":
        arrows = []
        for item in payload.get("arrows", []) if isinstance(payload.get("arrows", []), list) else []:
            if (
                isinstance(item, dict)
                and SQUARE_PATTERN.fullmatch(str(item.get("source", "")))
                and SQUARE_PATTERN.fullmatch(str(item.get("target", "")))
            ):
                try:
                    arrows.append(TutorArrow.model_validate(item))
                except ValueError:
                    pass
        highlights = []
        for item in payload.get("highlights", []) if isinstance(payload.get("highlights", []), list) else []:
            if isinstance(item, dict) and SQUARE_PATTERN.fullmatch(str(item.get("square", ""))):
                try:
                    highlights.append(TutorHighlight.model_validate(item))
                except ValueError:
                    pass
        key_squares = (
            [str(value) for value in payload.get("key_squares", []) if SQUARE_PATTERN.fullmatch(str(value))]
            if isinstance(payload.get("key_squares", []), list)
            else []
        )
        safe = dict(payload)
        safe["arrows"], safe["highlights"], safe["key_squares"] = arrows, highlights, key_squares
        return cls.model_validate(safe)

    @classmethod
    def parse_text(cls, content: str) -> "TutorResponse":
        try:
            payload = json.loads(content)
            if isinstance(payload, dict):
                return cls.from_payload(payload)
        except json.JSONDecodeError:
            pass
        return cls(summary=content)
