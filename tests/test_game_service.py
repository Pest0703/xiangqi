from xiangqi_tutor.board import Position, START_FEN
from xiangqi_tutor.models.core import Move, Side
from xiangqi_tutor.services import GameService


def test_move_undo_redo_and_new_game() -> None:
    game = GameService()
    first = game.move(Move.from_engine("h2e2"))
    assert first.chinese == "炮二平五"
    moved_fen = game.export_fen()
    assert game.position.side_to_move is Side.BLACK
    assert game.undo()
    assert game.export_fen() == START_FEN
    assert game.redo()
    assert game.export_fen() == moved_fen
    game.new_game()
    assert game.export_fen() == START_FEN and not game.records


def test_twenty_ply_sequence_and_full_undo_redo() -> None:
    game = GameService()
    start = game.export_fen()
    moves = []
    for _ in range(20):
        legal = game.position.legal_moves()
        assert legal
        move = legal[len(legal) // 2]
        moves.append(move)
        game.move(move)
    end = game.export_fen()
    assert len(game.records) == 20 and game.position.side_to_move is Side.RED
    for _ in range(20):
        assert game.undo()
    assert game.export_fen() == start
    for _ in range(20):
        assert game.redo()
    assert game.export_fen() == end


def test_load_fen_resets_history() -> None:
    game = GameService()
    game.move(Move.from_engine("h2e2"))
    game.load_fen(START_FEN.replace(" w ", " b "))
    assert game.position.side_to_move is Side.BLACK and not game.records

