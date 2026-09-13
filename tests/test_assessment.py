from xiangqi_tutor.board import START_FEN, Position
from xiangqi_tutor.models.core import Move, Side
from xiangqi_tutor.models.engine import AnalysisResult, CandidateMove
from xiangqi_tutor.services import AssessmentGrade, MoveAssessmentService


def analysis(fen: str, best: str, score: int, pv: tuple[str, ...]) -> AnalysisResult:
    candidate = CandidateMove(best, score, None, 12, 1000, pv, score)
    return AnalysisResult(fen, fen.split()[1], best, 12, 1000, score_raw=score, score_for_red=score, candidates=(candidate,))


def test_assessment_uses_user_view_and_validated_reply_pv() -> None:
    before = analysis(START_FEN, "h2e2", 40, ("h2e2", "h7e7"))
    position_after = Position.initial().apply_move(Move.from_engine("c3c4"))
    after = analysis(position_after.to_fen(), "h7e7", -180, ("h7e7", "h0g2", "a9a0"))
    result = MoveAssessmentService().assess(before=before, after=after, played_move="c3c4", user_side=Side.RED)
    assert result.evaluation_loss == 220
    assert result.grade is AssessmentGrade.MISTAKE
    assert result.opponent_best_reply == "h7e7"
    assert len(result.pv) == 2


def test_black_user_score_direction_and_best_move() -> None:
    fen = START_FEN.replace(" w ", " b ")
    before = analysis(fen, "h7e7", -60, ("h7e7",))
    after_position = Position.from_fen(fen).apply_move(Move.from_engine("h7e7"))
    after = analysis(after_position.to_fen(), "h2e2", -55, ("h2e2",))
    result = MoveAssessmentService().assess(before=before, after=after, played_move="h7e7", user_side=Side.BLACK)
    assert result.grade is AssessmentGrade.BEST
    assert result.score_before_for_user == 60 and result.score_after_for_user == 55
