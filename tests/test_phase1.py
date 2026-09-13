from contextlib import closing
from pathlib import Path

from xiangqi_tutor.database.connection import Database
from xiangqi_tutor.engine.discovery import discover_pikafish
from xiangqi_tutor.engine.protocol import parse_info_line
from xiangqi_tutor.models.core import Move, Square


def test_square_and_move_engine_round_trip() -> None:
    assert Square.from_engine("a0").engine == "a0"
    assert Move.from_engine("h2e2").engine == "h2e2"


def test_parse_multipv_info() -> None:
    parsed = parse_info_line("info depth 18 multipv 2 score cp 31 nodes 4567 pv h2e2 h9g7")
    assert parsed is not None
    index, candidate = parsed
    assert index == 2
    assert candidate.move == "h2e2"
    assert candidate.score_cp == 31
    assert candidate.pv == ("h2e2", "h9g7")


def test_database_initializes(tmp_path: Path) -> None:
    database = Database(tmp_path / "test.sqlite3")
    database.initialize()
    with closing(database.connect()) as connection, connection:
        version = connection.execute("SELECT value FROM schema_meta WHERE key='version'").fetchone()[0]
    assert version == "1"


def test_missing_engine_is_nonfatal(tmp_path: Path) -> None:
    assert discover_pikafish(tmp_path / "missing.exe") is None
