import sys
from pathlib import Path

from xiangqi_tutor.board import START_FEN
from xiangqi_tutor.engine import EngineService
from xiangqi_tutor.engine.protocol import normalize_score_for_red, parse_info_line
from xiangqi_tutor.models.engine import ScoreKind


def test_score_direction_for_both_sides() -> None:
    assert normalize_score_for_red(35, "w") == 35
    assert normalize_score_for_red(35, "b") == -35


def test_fake_uci_end_to_end_multipv_order() -> None:
    script = Path(__file__).with_name("fake_uci_engine.py")
    with EngineService(sys.executable, args=("-u", str(script)), timeout=3) as engine:
        engine.configure(threads=2, hash_mb=64, multipv=3)
        result = engine.analyze(START_FEN, depth=12)
    assert result.best_move == "h2e2"
    assert [candidate.move for candidate in result.candidates] == ["h2e2", "b0c2", "c3c4"]
    assert result.score_for_red == 35 and result.depth == 12 and result.nodes == 1000


def test_black_score_is_normalized_to_red_view() -> None:
    script = Path(__file__).with_name("fake_uci_engine.py")
    black_fen = START_FEN.replace(" w ", " b ")
    with EngineService(sys.executable, args=("-u", str(script)), timeout=3) as engine:
        result = engine.analyze(black_fen, depth=12)
    assert result.score_raw == 40 and result.score_for_red == -40


def test_mate_score_keeps_kind_and_normalizes_winner() -> None:
    parsed = parse_info_line("info depth 20 multipv 1 score mate 3 nodes 1 pv h2e2", side_to_move="b")
    assert parsed is not None
    candidate = parsed[1]
    assert candidate.evaluation and candidate.evaluation.kind is ScoreKind.MATE
    assert candidate.evaluation.score_for_red == -3
    assert candidate.evaluation.for_red_text() == "黑方3步杀"
