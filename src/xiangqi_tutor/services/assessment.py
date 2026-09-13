from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from xiangqi_tutor.board import Position
from xiangqi_tutor.engine import PVValidator, ValidatedPVStep
from xiangqi_tutor.models.core import Side
from xiangqi_tutor.models.engine import AnalysisResult, ScoreKind


class AssessmentGrade(StrEnum):
    BEST = "best"
    EXCELLENT = "excellent"
    GOOD = "good"
    INACCURACY = "inaccuracy"
    MISTAKE = "mistake"
    BLUNDER = "blunder"


@dataclass(frozen=True, slots=True)
class MoveAssessment:
    fen_before: str
    fen_after: str
    user_side: Side
    best_move: str | None
    played_move: str
    score_before_for_user: int | None
    score_after_for_user: int | None
    evaluation_loss: int | None
    opponent_best_reply: str | None
    grade: AssessmentGrade
    pv: tuple[ValidatedPVStep, ...]


class MoveAssessmentService:
    def __init__(self, thresholds: tuple[int, int, int, int] = (20, 60, 120, 250)) -> None:
        self.thresholds = thresholds

    @staticmethod
    def _for_user(score_for_red: int | None, side: Side) -> int | None:
        if score_for_red is None:
            return None
        return score_for_red if side is Side.RED else -score_for_red

    def assess(
        self,
        *,
        before: AnalysisResult,
        after: AnalysisResult,
        played_move: str,
        user_side: Side,
    ) -> MoveAssessment:
        if before.fen.split()[1] != user_side.value:
            raise ValueError("走前分析的行棋方与用户阵营不一致")
        position_after = Position.from_fen(after.fen)
        before_user = self._for_user(before.score_for_red, user_side)
        after_user = self._for_user(after.score_for_red, user_side)
        loss = None if before_user is None or after_user is None else max(0, before_user - after_user)
        if played_move == before.best_move:
            grade = AssessmentGrade.BEST
        elif self._mate_was_lost(before, after, user_side):
            grade = AssessmentGrade.BLUNDER
        elif loss is None:
            grade = AssessmentGrade.GOOD
        else:
            scale = 1.5 if before_user is not None and abs(before_user) >= 500 else 1.0
            excellent, good, inaccurate, mistake = (round(value * scale) for value in self.thresholds)
            if loss <= excellent:
                grade = AssessmentGrade.EXCELLENT
            elif loss <= good:
                grade = AssessmentGrade.GOOD
            elif loss <= inaccurate:
                grade = AssessmentGrade.INACCURACY
            elif loss <= mistake:
                grade = AssessmentGrade.MISTAKE
            else:
                grade = AssessmentGrade.BLUNDER
        pv = PVValidator.validate(position_after, after.candidates[0].pv if after.candidates else ())
        return MoveAssessment(
            fen_before=before.fen,
            fen_after=after.fen,
            user_side=user_side,
            best_move=before.best_move,
            played_move=played_move,
            score_before_for_user=before_user,
            score_after_for_user=after_user,
            evaluation_loss=loss,
            opponent_best_reply=after.best_move,
            grade=grade,
            pv=pv,
        )

    @staticmethod
    def _mate_was_lost(before: AnalysisResult, after: AnalysisResult, side: Side) -> bool:
        if not before.candidates or not before.candidates[0].evaluation:
            return False
        score = before.candidates[0].evaluation
        if score.kind is not ScoreKind.MATE or score.score_for_red is None:
            return False
        before_winning = score.score_for_red > 0 if side is Side.RED else score.score_for_red < 0
        if not before_winning:
            return False
        if not after.candidates or not after.candidates[0].evaluation:
            return True
        after_score = after.candidates[0].evaluation
        return after_score.kind is not ScoreKind.MATE or (
            after_score.score_for_red is not None
            and ((after_score.score_for_red <= 0) if side is Side.RED else (after_score.score_for_red >= 0))
        )
