from __future__ import annotations

import json
from enum import StrEnum
from typing import Any, Mapping

from xiangqi_tutor.tutor.evidence import TutorEvidence
from xiangqi_tutor.tutor.provider import TutorRequest
from xiangqi_tutor.tutor.system_prompt import SYSTEM_PROMPT


class TutorTask(StrEnum):
    EXPLAIN_MOVE = "explain_move"
    COMPARE_MOVES = "compare_moves"
    REVIEW_GAME = "review_game"
    OPENING_HELP = "opening_help"
    ENDGAME_HELP = "endgame_help"
    HINT = "hint"
    FREE_QUESTION = "free_question"


class UserLevel(StrEnum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class HintLevel(StrEnum):
    HINT_1 = "Hint 1"
    HINT_2 = "Hint 2"
    HINT_3 = "Hint 3"
    ANSWER = "Answer"


TASK_INSTRUCTIONS: dict[TutorTask, str] = {
    TutorTask.EXPLAIN_MOVE: "解释用户走法的目的、具体问题、强回应与更好选择。",
    TutorTask.COMPARE_MOVES: "比较各候选计划及评价差异，不只排列分数。",
    TutorTask.REVIEW_GAME: "只解释程序筛选出的关键局面，并归纳可迁移的学习问题。",
    TutorTask.OPENING_HELP: "先讲当前布局目标；输入未确认开局名称时不得自行命名。",
    TutorTask.ENDGAME_HELP: "解释残局目标、计算次序和转换方法，不编造未验证答案。",
    TutorTask.HINT: "严格遵守指定提示等级，不提前泄露更高等级信息。",
    TutorTask.FREE_QUESTION: "回答用户问题，并把结论限制在当前局面与引擎证据内。",
}


class PromptBuilder:
    """按任务构造小而明确的提示；默认只接受调用方筛选后的最近走法。"""

    def __init__(self, *, max_recent_moves: int = 8) -> None:
        if max_recent_moves < 1:
            raise ValueError("max_recent_moves 必须大于零")
        self.max_recent_moves = max_recent_moves

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def build(
        self,
        *,
        task: TutorTask,
        fen: str,
        side_to_move: str,
        level: UserLevel,
        recent_moves: list[str] | tuple[str, ...] = (),
        engine_analysis: Mapping[str, Any] | None = None,
        played_move: str | None = None,
        question: str = "",
        hint_level: HintLevel | None = None,
        request_visuals: bool = False,
        extra_context: Mapping[str, Any] | None = None,
    ) -> TutorRequest:
        if not fen.strip():
            raise ValueError("导师请求必须包含当前 FEN")
        if task is TutorTask.HINT and hint_level is None:
            raise ValueError("提示任务必须指定 hint_level")

        context: dict[str, Any] = {
            "fen": fen,
            "side_to_move": side_to_move,
            "level": level.value,
            "recent_moves": list(recent_moves[-self.max_recent_moves :]),
            "played_move": played_move,
            "engine_analysis": dict(engine_analysis or {}),
            "hint_level": hint_level.value if hint_level else None,
            "request_visuals": request_visuals,
        }
        if extra_context:
            context["extra_context"] = dict(extra_context)

        instruction = TASK_INSTRUCTIONS[task]
        user_prompt = (
            f"【任务】{task.value}\n"
            f"【任务要求】{instruction}\n"
            f"【结构化局面数据】\n{json.dumps(context, ensure_ascii=False, separators=(',', ':'))}\n"
            f"【用户问题】{question.strip() or '无'}"
        )
        return TutorRequest(
            task=task.value,
            context={
                "system_prompt": self.system_prompt,
                "user_prompt": user_prompt,
                "position_context": context,
            },
            question=question,
        )

    def build_from_evidence(
        self,
        *,
        task: TutorTask,
        evidence: TutorEvidence,
        level: UserLevel,
        question: str = "",
        hint_level: HintLevel | None = None,
        request_visuals: bool = False,
    ) -> TutorRequest:
        data = evidence.to_dict()
        return self.build(
            task=task,
            fen=evidence.fen,
            side_to_move=evidence.side_to_move,
            level=level,
            recent_moves=list(evidence.recent_moves),
            engine_analysis={
                "best_move": evidence.best_move,
                "candidate_moves": data["candidate_moves"],
                "score_for_red": evidence.score_for_red,
                "pv": data["validated_pv"] or evidence.pv,
            },
            played_move=evidence.played_move,
            question=question,
            hint_level=hint_level,
            request_visuals=request_visuals,
            extra_context={
                "pieces": data["pieces"],
                "legal_moves": evidence.legal_moves,
                "last_move": evidence.last_move,
                "branch_id": evidence.branch_id,
                "request_id": evidence.request_id,
                "position_version": evidence.position_version,
            },
        )
