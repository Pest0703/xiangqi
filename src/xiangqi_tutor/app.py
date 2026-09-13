from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

_DLL_DIRECTORY_HANDLES: list[object] = []


def _prepare_frozen_dll_search_path() -> None:
    """让冻结版在 Windows 上先找到 Qt/Shiboken 的相邻 DLL。"""
    if not (sys.platform == "win32" and getattr(sys, "frozen", False)):
        return
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    for relative in ("PySide6", "shiboken6"):
        directory = bundle_root / relative
        if directory.is_dir():
            _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(directory)))


_prepare_frozen_dll_search_path()

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from xiangqi_tutor.config import AppSettings
from xiangqi_tutor.database.connection import Database
from xiangqi_tutor.ui.main_window import MainWindow


def configure_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "xiangqi-tutor.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def main() -> int:
    settings = AppSettings()
    configure_logging(settings.log_dir)
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("中国象棋私人导师")
    app.setOrganizationName("XiangqiTutor")
    try:
        database = Database(settings.database_path)
        database.initialize()
        window = MainWindow(settings=settings, database=database)
        window.show()
        return app.exec()
    except Exception as exc:  # GUI 边界：不给普通用户展示 traceback
        logging.getLogger(__name__).exception("应用启动失败")
        QMessageBox.critical(None, "启动失败", f"软件无法启动：{exc}\n详细信息已写入日志。")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
