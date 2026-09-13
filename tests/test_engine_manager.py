import sys
from pathlib import Path

from xiangqi_tutor.board import START_FEN
from xiangqi_tutor.database.connection import Database
from xiangqi_tutor.engine import EngineJob, EngineManager


def test_engine_manager_reuses_one_process_for_multiple_jobs() -> None:
    script = Path(__file__).with_name("fake_uci_engine.py")
    manager = EngineManager(Path(sys.executable), args=("-u", str(script)), timeout=3)
    try:
        first = manager.submit(EngineJob("one", START_FEN, 0, 12, 0, 3)).result(timeout=5)
        service = manager._service
        pid = service.process.pid if service and service.process else None
        second = manager.submit(EngineJob("two", START_FEN, 0, 12, 0, 3)).result(timeout=5)
        assert first and second and first.analysis.best_move == second.analysis.best_move
        assert service is manager._service and manager._service.process.pid == pid
    finally:
        manager.close()


def test_engine_manager_uses_persistent_database_cache(tmp_path: Path) -> None:
    script = Path(__file__).with_name("fake_uci_engine.py")
    database = Database(tmp_path / "engine-cache.sqlite3")
    database.initialize()
    job = EngineJob("first", START_FEN, 0, 12, 0, 3)
    first = EngineManager(Path(sys.executable), args=("-u", str(script)), timeout=3, database=database)
    try:
        assert first.submit(job).result(timeout=5)
    finally:
        first.close()
    second = EngineManager(Path(sys.executable), args=("-u", str(script)), timeout=3, database=database)
    try:
        cached = second.submit(EngineJob("second", START_FEN, 0, 12, 0, 3)).result(timeout=5)
        assert cached and cached.analysis.best_move == "h2e2"
        assert second._service is None
    finally:
        second.close()
