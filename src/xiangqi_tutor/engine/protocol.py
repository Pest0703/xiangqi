from __future__ import annotations

import re

from xiangqi_tutor.models.engine import CandidateMove


_INTEGER_FIELDS = {"depth", "nodes", "multipv"}


def parse_info_line(line: str) -> tuple[int, CandidateMove] | None:
    """解析 Pikafish/Stockfish 风格的完整 UCI info PV 行。"""
    tokens = line.strip().split()
    if not tokens or tokens[0] != "info" or "pv" not in tokens or "score" not in tokens:
        return None
    values: dict[str, int] = {"depth": 0, "nodes": 0, "multipv": 1}
    for field in _INTEGER_FIELDS:
        if field in tokens:
            index = tokens.index(field)
            if index + 1 < len(tokens) and re.fullmatch(r"-?\d+", tokens[index + 1]):
                values[field] = int(tokens[index + 1])
    score_index = tokens.index("score")
    score_cp = mate = None
    if score_index + 2 < len(tokens):
        score_kind, raw_score = tokens[score_index + 1 : score_index + 3]
        if re.fullmatch(r"-?\d+", raw_score):
            if score_kind == "cp":
                score_cp = int(raw_score)
            elif score_kind == "mate":
                mate = int(raw_score)
    pv_index = tokens.index("pv")
    pv = tuple(tokens[pv_index + 1 :])
    if not pv:
        return None
    candidate = CandidateMove(
        move=pv[0], score_cp=score_cp, mate=mate,
        depth=values["depth"], nodes=values["nodes"], pv=pv,
    )
    return values["multipv"], candidate

