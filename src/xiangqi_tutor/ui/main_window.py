from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel, QMainWindow, QPushButton, QSplitter, QTabWidget,
    QTextEdit, QToolBar, QVBoxLayout, QWidget,
)

from xiangqi_tutor.config import AppSettings
from xiangqi_tutor.database.connection import Database
from xiangqi_tutor.engine.discovery import discover_nnue, discover_pikafish


class MainWindow(QMainWindow):
    def __init__(self, settings: AppSettings, database: Database) -> None:
        super().__init__()
        self.settings = settings
        self.database = database
        self.setWindowTitle("中国象棋私人导师")
        self.resize(1366, 768)
        self.setMinimumSize(1024, 650)
        self._build_toolbar()
        self._build_content()
        self._apply_style()
        self._show_engine_status()

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("主要功能", self)
        toolbar.setMovable(False)
        for label in ("新对局", "打开棋谱", "训练", "残局", "沙盘", "复盘", "设置"):
            action = toolbar.addAction(label)
            action.setEnabled(False)
            action.setToolTip(f"{label}尚未实现，当前测试版仅用于验证工程骨架")
        self.addToolBar(toolbar)

    def _build_content(self) -> None:
        board = QWidget()
        board_layout = QVBoxLayout(board)
        title = QLabel("九路十行棋盘")
        title.setObjectName("boardTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder = QLabel("Phase 2 完成规则层后，在此接入可交互棋盘")
        placeholder.setObjectName("boardPlaceholder")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        board_layout.addWidget(title)
        board_layout.addWidget(placeholder, 1)

        tabs = QTabWidget()
        self.tutor_text = QTextEdit()
        self.tutor_text.setReadOnly(True)
        self.tutor_text.setPlainText("导师将基于 Pikafish 证据解释走法，而不是自行猜测最佳着。")
        self.engine_text = QTextEdit()
        self.engine_text.setReadOnly(True)
        tabs.addTab(self.tutor_text, "导师")
        tabs.addTab(self.engine_text, "引擎")
        tabs.addTab(QLabel("棋谱浏览将在后续阶段接入。"), "棋谱")
        tabs.addTab(QLabel("主线与沙盘分支将在后续阶段接入。"), "变化树")

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(board)
        splitter.addWidget(tabs)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([820, 500])
        self.setCentralWidget(splitter)
        self.statusBar().showMessage("技术预览版：对局与教学功能尚未实现")

    def _show_engine_status(self) -> None:
        engine = discover_pikafish(self.settings.pikafish_path)
        network = discover_nnue(engine, self.settings.pikafish_nnue_path)
        if not engine:
            self.engine_text.setPlainText(
                "未检测到 Pikafish。\n\n软件仍可启动；请在后续设置页选择 pikafish.exe。"
            )
            return
        self.engine_text.setPlainText(
            f"已检测到引擎：{engine}\nNNUE：{network or '未检测到'}"
        )

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow { background: #f3f1eb; color: #262521; }
            QToolBar { background: #252724; spacing: 8px; padding: 8px; border: 0; }
            QToolButton { color: #f6f3eb; padding: 7px 11px; }
            QTabWidget::pane { border: 1px solid #d3cec2; background: #fffdf8; }
            QTabBar::tab { padding: 9px 18px; background: #e7e2d8; }
            QTabBar::tab:selected { background: #fffdf8; color: #8b2f25; }
            #boardTitle { font-size: 20px; font-weight: 600; padding: 10px; }
            #boardPlaceholder { border: 1px solid #b5aa95; background: #dfc38e; font-size: 16px; }
            QTextEdit { border: 0; padding: 12px; background: #fffdf8; }
            """
        )
