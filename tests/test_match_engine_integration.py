import sys
from pathlib import Path

from xiangqi_tutor.engine import EngineJob, EngineManager
from xiangqi_tutor.models.core import Move, Side
from xiangqi_tutor.services import GameMode, MatchService


def wire(match: MatchService, manager: EngineManager) -> None:
    match.engine_move_requested.connect(
        lambda request: manager.submit(EngineJob(request.request_id, request.fen, request.position_version, request.depth, 0, 1))
    )
    manager.completed.connect(
        lambda result: match.apply_engine_move(
            result.job.request_id,
            result.job.fen,
            result.job.position_version,
            result.analysis.best_move,
        )
    )


def test_human_red_gets_automatic_engine_reply(qtbot) -> None:
    manager = EngineManager(Path(sys.executable), args=("-u", str(Path(__file__).with_name("fake_uci_engine.py"))), timeout=3)
    match = MatchService()
    wire(match, manager)
    try:
        match.new_match(GameMode.HUMAN_VS_ENGINE, Side.RED)
        match.make_human_move(Move.from_engine("h2e2"))
        qtbot.waitUntil(lambda: len(match.game.records) == 2, timeout=3000)
        assert match.can_human_move and match.game.position.side_to_move is Side.RED
    finally:
        manager.close()


def test_human_black_receives_automatic_red_opening(qtbot) -> None:
    manager = EngineManager(Path(sys.executable), args=("-u", str(Path(__file__).with_name("fake_uci_engine.py"))), timeout=3)
    match = MatchService()
    wire(match, manager)
    try:
        match.new_match(GameMode.HUMAN_VS_ENGINE, Side.BLACK)
        qtbot.waitUntil(lambda: len(match.game.records) == 1, timeout=3000)
        assert match.can_human_move and match.game.position.side_to_move is Side.BLACK
    finally:
        manager.close()
