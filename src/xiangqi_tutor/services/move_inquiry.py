from __future__ import annotations

from dataclasses import dataclass

from xiangqi_tutor.board import Position
from xiangqi_tutor.models.core import Move, Side
from xiangqi_tutor.models.engine import AnalysisResult
from xiangqi_tutor.services.assessment import MoveAssessment, MoveAssessmentService


@dataclass(frozen=True, slots=True)
class MoveInquiry:
    move: str
    legal: bool
    rule_explanation: str | None = None
    assessment: MoveAssessment | None = None


class MoveInquiryService:
    def __init__(self, assessment_service: MoveAssessmentService | None = None) -> None:
        self.assessment_service = assessment_service or MoveAssessmentService()

    def inspect(
        self,
        position: Position,
        move: Move,
        *,
        before_analysis: AnalysisResult | None = None,
        after_analysis: AnalysisResult | None = None,
        user_side: Side | None = None,
    ) -> MoveInquiry:
        piece = position.piece_at(move.source)
        if piece is None:
            return MoveInquiry(move.engine, False, "起点没有棋子。")
        if piece.side is not position.side_to_move:
            return MoveInquiry(move.engine, False, "现在不是这方行棋。")
        pseudo = tuple(position.pseudo_moves_from(move.source))
        if move not in pseudo:
            return MoveInquiry(move.engine, False, "这一步不符合该棋子的基本走法，或者移动路径被棋子阻挡。")
        if move not in position.legal_moves_from(move.source):
            return MoveInquiry(move.engine, False, "这一步走后会让己方将帅仍处于被攻击状态，或造成将帅照面。")
        assessment = None
        if before_analysis and after_analysis and user_side:
            assessment = self.assessment_service.assess(
                before=before_analysis,
                after=after_analysis,
                played_move=move.engine,
                user_side=user_side,
            )
        return MoveInquiry(move.engine, True, None, assessment)
