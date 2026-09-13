import pytest

from xiangqi_tutor.tutor.prompt_builder import HintLevel, PromptBuilder, TutorTask, UserLevel


FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"


def test_prompt_contains_engine_authority_and_evidence_boundary() -> None:
    request = PromptBuilder().build(
        task=TutorTask.EXPLAIN_MOVE,
        fen=FEN,
        side_to_move="b",
        level=UserLevel.BEGINNER,
        played_move="h2e2",
        engine_analysis={"best_move": "h2e2", "eval_before": 20, "eval_after": 18},
    )
    system = request.context["system_prompt"]
    assert "引擎负责判断棋力，你负责解释" in system
    assert "从当前引擎数据暂时无法确定这一点" in system
    assert request.context["position_context"]["played_move"] == "h2e2"


def test_recent_moves_are_bounded() -> None:
    request = PromptBuilder(max_recent_moves=4).build(
        task=TutorTask.FREE_QUESTION,
        fen=FEN,
        side_to_move="w",
        level=UserLevel.INTERMEDIATE,
        recent_moves=[f"m{i}" for i in range(10)],
        question="我现在最大的弱点是什么？",
    )
    assert request.context["position_context"]["recent_moves"] == ["m6", "m7", "m8", "m9"]


def test_hint_requires_level_and_does_not_default_to_answer() -> None:
    with pytest.raises(ValueError, match="hint_level"):
        PromptBuilder().build(
            task=TutorTask.HINT,
            fen=FEN,
            side_to_move="w",
            level=UserLevel.BEGINNER,
        )
    request = PromptBuilder().build(
        task=TutorTask.HINT,
        fen=FEN,
        side_to_move="w",
        level=UserLevel.BEGINNER,
        hint_level=HintLevel.HINT_1,
    )
    assert request.context["position_context"]["hint_level"] == "Hint 1"


def test_visual_schema_is_constrained() -> None:
    system = PromptBuilder().system_prompt
    assert '"arrows": []' in system
    assert "recommended、danger、plan" in system

