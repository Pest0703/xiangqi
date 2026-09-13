from pathlib import Path

from PySide6.QtCore import Qt

from xiangqi_tutor.config import AppSettings
from xiangqi_tutor.database.connection import Database
from xiangqi_tutor.models.core import Square
from xiangqi_tutor.tutor import TutorTask
from xiangqi_tutor.ui.main_window import MainWindow


def make_window(qtbot, tmp_path: Path) -> MainWindow:
    settings = AppSettings(database_path=tmp_path / "gui.sqlite3")
    database = Database(settings.database_path)
    database.initialize()
    window = MainWindow(settings, database)
    qtbot.addWidget(window)
    return window


def test_gui_starts_at_supported_minimum(qtbot, tmp_path: Path) -> None:
    window = make_window(qtbot, tmp_path)
    window.show()
    qtbot.waitExposed(window)
    assert window.minimumWidth() == 1050
    assert window.minimumHeight() == 700
    assert window.centralWidget().orientation() == Qt.Orientation.Horizontal


def test_mvp_toolbar_actions_enabled_and_future_actions_disabled(qtbot, tmp_path: Path) -> None:
    window = make_window(qtbot, tmp_path)
    assert window.actions["新对局"].isEnabled()
    assert window.actions["翻转棋盘"].isEnabled()
    assert window.actions["复制FEN"].isEnabled()
    assert all(not window.actions[name].isEnabled() for name in ("训练", "残局", "复盘"))


def test_board_click_move_updates_history_and_flip_preserves_logic(qtbot, tmp_path: Path) -> None:
    window = make_window(qtbot, tmp_path)
    window.resize(1366, 820)
    window.show()
    qtbot.waitExposed(window)
    before = window.game.export_fen()
    qtbot.mouseClick(
        window.board_widget, Qt.MouseButton.LeftButton, pos=window.board_widget._screen_point(Square.from_engine("h2")).toPoint()
    )
    qtbot.mouseClick(
        window.board_widget, Qt.MouseButton.LeftButton, pos=window.board_widget._screen_point(Square.from_engine("e2")).toPoint()
    )
    assert len(window.game.records) == 1
    assert window.history.count() == 1
    logical = window.game.export_fen()
    window.board_widget.flip()
    assert window.game.export_fen() == logical and logical != before


def test_board_coordinate_mapping_round_trips_before_and_after_flip(qtbot, tmp_path: Path) -> None:
    window = make_window(qtbot, tmp_path)
    window.resize(1366, 820)
    for engine_square in ("a0", "i0", "a9", "i9", "e4"):
        square = Square.from_engine(engine_square)
        assert window.board_widget.square_at(window.board_widget._screen_point(square)) == square
    window.board_widget.flip()
    for engine_square in ("a0", "i0", "a9", "i9", "e4"):
        square = Square.from_engine(engine_square)
        assert window.board_widget.square_at(window.board_widget._screen_point(square)) == square


def test_tutor_task_routing_is_not_all_free_question(qtbot, tmp_path: Path) -> None:
    window = make_window(qtbot, tmp_path)
    assert window._route_tutor_task("比较前两个候选") is TutorTask.COMPARE_MOVES
    assert window._route_tutor_task("为什么这一步不好") is TutorTask.EXPLAIN_MOVE
    assert window._route_tutor_task("给我提示") is TutorTask.HINT
