from pathlib import Path

from xiangqi_tutor.database.connection import Database


def test_engine_and_tutor_cache_round_trip(tmp_path: Path) -> None:
    database = Database(tmp_path / "cache.sqlite3")
    database.initialize()
    database.put_engine_cache("e", "fen", {"depth": 12}, {"best_move": "h2e2"})
    assert database.get_engine_cache("e") == {"best_move": "h2e2"}
    database.put_tutor_cache("t", "fen", "qwen-plus", {"content": "解释"})
    assert database.get_tutor_cache("t") == {"content": "解释"}
