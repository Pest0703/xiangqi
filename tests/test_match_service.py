import pytest

from xiangqi_tutor.board import IllegalMoveError
from xiangqi_tutor.models.core import Move, Side
from xiangqi_tutor.services import EngineStrength, GameMode, MatchService, MatchState


def test_human_red_engine_reply_and_decision_undo_redo() -> None:
    match = MatchService()
    requests = []
    match.engine_move_requested.connect(requests.append)
    match.new_match(GameMode.HUMAN_VS_ENGINE, Side.RED, EngineStrength.CASUAL)
    match.make_human_move(Move.from_engine("h2e2"))
    assert match.state is MatchState.ENGINE_THINKING and len(requests) == 1
    request = requests[-1]
    reply = match.game.position.legal_moves()[0]
    assert match.apply_engine_move(request.request_id, request.fen, request.position_version, reply.engine)
    assert match.state is MatchState.WAITING_FOR_HUMAN and len(match.game.records) == 2
    assert match.undo_decision() and not match.game.records
    assert match.redo_decision() and len(match.game.records) == 2


def test_human_black_causes_engine_to_open_and_blocks_input() -> None:
    match = MatchService()
    requests = []
    match.engine_move_requested.connect(requests.append)
    match.new_match(GameMode.HUMAN_VS_ENGINE, Side.BLACK)
    assert match.state is MatchState.ENGINE_THINKING and requests
    with pytest.raises(IllegalMoveError):
        match.make_human_move(Move.from_engine("h2e2"))
    request = requests[-1]
    opening = match.game.position.legal_moves()[0]
    assert match.apply_engine_move(request.request_id, request.fen, request.position_version, opening.engine)
    assert match.can_human_move and match.game.position.side_to_move is Side.BLACK


def test_stale_or_illegal_engine_move_is_rejected() -> None:
    match = MatchService()
    requests = []
    errors = []
    match.engine_move_requested.connect(requests.append)
    match.engine_error.connect(errors.append)
    match.new_match(GameMode.HUMAN_VS_ENGINE, Side.BLACK)
    request = requests[-1]
    assert not match.apply_engine_move("stale", request.fen, request.position_version, "h2e2")
    assert not match.apply_engine_move(request.request_id, request.fen, request.position_version, "a0a9")
    assert errors and match.state is MatchState.WAITING_FOR_HUMAN
