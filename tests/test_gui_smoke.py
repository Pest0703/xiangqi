from pathlib import Path

from PySide6.QtCore import Qt

from xiangqi_tutor.config import AppSettings
from xiangqi_tutor.database.connection import Database
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
    assert window.minimumWidth() == 1024
    assert window.minimumHeight() == 650
    assert window.centralWidget().orientation() == Qt.Orientation.Horizontal


def test_unimplemented_toolbar_actions_are_not_misleading(qtbot, tmp_path: Path) -> None:
    window = make_window(qtbot, tmp_path)
    actions = [action for action in window.findChildren(type(window.menuBar().addAction("probe"))) if action.text() != "probe"]
    toolbar_actions = [action for action in actions if action.text() in {"新对局", "打开棋谱", "训练", "残局", "沙盘", "复盘", "设置"}]
    assert len(toolbar_actions) == 7
    assert all(not action.isEnabled() for action in toolbar_actions)

