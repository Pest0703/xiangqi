from __future__ import annotations

import keyring
from pathlib import Path
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QInputDialog, QLabel, QListWidget, QMainWindow,
    QMessageBox, QPushButton, QSplitter, QTabWidget, QTextEdit, QToolBar,
    QVBoxLayout, QWidget,
)

from xiangqi_tutor.board import IllegalMoveError
from xiangqi_tutor.config import AppSettings
from xiangqi_tutor.database.connection import Database
from xiangqi_tutor.engine.discovery import discover_nnue, discover_pikafish
from xiangqi_tutor.models.engine import AnalysisResult
from xiangqi_tutor.models.core import Move, Side
from xiangqi_tutor.notation import move_to_chinese
from xiangqi_tutor.services import GameService
from xiangqi_tutor.tutor import EvidenceCandidate, EvidencePiece, HintLevel, PromptBuilder, TutorEvidence, TutorTask, UserLevel
from xiangqi_tutor.ui.board_widget import XiangqiBoardWidget
from xiangqi_tutor.ui.settings_dialog import KEYRING_SERVICE, KEYRING_USER, SettingsDialog
from xiangqi_tutor.ui.workers import EngineAnalysisThread, TutorThread


class MainWindow(QMainWindow):
    def __init__(self, settings: AppSettings, database: Database) -> None:
        super().__init__()
        self.settings = settings
        self.database = database
        self.game = GameService()
        self.store = QSettings("XiangqiTutor", "XiangqiTutor")
        self.analysis_result: AnalysisResult | None = None
        self.engine_thread: EngineAnalysisThread | None = None
        self.tutor_thread: TutorThread | None = None
        self.setWindowTitle("中国象棋私人导师")
        self.resize(1366, 820)
        self.setMinimumSize(1050, 700)
        self.actions: dict[str, QAction] = {}
        self._build_toolbar()
        self._build_content()
        self._connect_game()
        self._apply_style()
        self._show_engine_status()
        self._refresh_position()

    def _add_action(self, toolbar: QToolBar, label: str, callback, *, enabled: bool = True) -> QAction:
        action = toolbar.addAction(label)
        action.setEnabled(enabled)
        if callback:
            action.triggered.connect(callback)
        self.actions[label] = action
        return action

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("主要功能", self)
        toolbar.setMovable(False)
        self._add_action(toolbar, "新对局", self._new_game)
        self._add_action(toolbar, "悔棋", self._undo)
        self._add_action(toolbar, "重做", self._redo)
        self._add_action(toolbar, "翻转棋盘", self._flip)
        toolbar.addSeparator()
        self._add_action(toolbar, "复制FEN", self._copy_fen)
        self._add_action(toolbar, "载入FEN", self._load_fen)
        self._add_action(toolbar, "分析", self._analyze)
        self._add_action(toolbar, "设置", self._settings)
        toolbar.addSeparator()
        for label in ("训练", "残局", "复盘"):
            action = self._add_action(toolbar, label, None, enabled=False)
            action.setToolTip("MVP 后续功能")
        self.addToolBar(toolbar)

    def _build_content(self) -> None:
        self.board_widget = XiangqiBoardWidget(self.game)
        self.turn_label = QLabel()
        self.turn_label.setObjectName("turnLabel")
        self.history = QListWidget()
        self.history.setMinimumHeight(130)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(self.turn_label)
        left_layout.addWidget(self.board_widget, 1)
        left_layout.addWidget(QLabel("走棋记录"))
        left_layout.addWidget(self.history)

        self.tabs = QTabWidget()
        tutor_page = QWidget()
        tutor_layout = QVBoxLayout(tutor_page)
        self.tutor_text = QTextEdit(readOnly=True)
        self.tutor_text.setPlainText("先在棋盘上思考和走棋。配置引擎后，导师会依据分析解释候选着。")
        self.question_input = QTextEdit()
        self.question_input.setPlaceholderText("询问当前局面，例如：为什么推荐这一步？")
        self.question_input.setMaximumHeight(100)
        quick = QHBoxLayout()
        for text in ("为什么推荐？", "这步有何问题？", "只给提示"):
            button = QPushButton(text)
            button.clicked.connect(lambda checked=False, value=text: self.question_input.setPlainText(value))
            quick.addWidget(button)
        self.send_button = QPushButton("发送给导师")
        self.send_button.clicked.connect(self._ask_tutor)
        tutor_layout.addWidget(self.tutor_text, 1)
        tutor_layout.addLayout(quick)
        tutor_layout.addWidget(self.question_input)
        tutor_layout.addWidget(self.send_button)

        engine_page = QWidget()
        engine_layout = QVBoxLayout(engine_page)
        self.engine_text = QTextEdit(readOnly=True)
        self.candidates = QListWidget()
        engine_layout.addWidget(self.engine_text)
        engine_layout.addWidget(QLabel("MultiPV候选着"))
        engine_layout.addWidget(self.candidates, 1)
        self.tabs.addTab(tutor_page, "导师")
        self.tabs.addTab(engine_page, "引擎")

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([820, 500])
        self.setCentralWidget(splitter)

    def _connect_game(self) -> None:
        self.board_widget.move_attempted.connect(self._make_move)
        self.game.position_changed.connect(lambda _: self._refresh_position())
        self.game.game_over.connect(lambda message: QMessageBox.information(self, "对局结束", message))

    def _make_move(self, move: Move) -> None:
        try:
            self.game.move(move)
        except IllegalMoveError as exc:
            self.statusBar().showMessage(str(exc), 3000)

    def _refresh_position(self) -> None:
        if self.engine_thread and self.engine_thread.isRunning():
            self.engine_thread.cancel()
        self.analysis_result = None
        self.candidates.clear()
        position = self.game.position
        side = "红方" if position.side_to_move is Side.RED else "黑方"
        check = " · 将军" if position.is_in_check(position.side_to_move) else ""
        self.turn_label.setText(f"轮到：{side}{check}")
        self.history.clear()
        records = self.game.records
        for index in range(0, len(records), 2):
            red = f"{records[index].chinese} ({records[index].move.engine})"
            black = ""
            if index + 1 < len(records):
                black = f"    {records[index+1].chinese} ({records[index+1].move.engine})"
            self.history.addItem(f"{index // 2 + 1}. {red}{black}")
        self.actions["悔棋"].setEnabled(bool(records))
        self.actions["重做"].setEnabled(self.game.can_redo)
        self.board_widget.update()
        self.statusBar().showMessage(f"{side}行棋 · {position.to_fen()}")

    def _new_game(self) -> None:
        self.game.new_game()
        self.candidates.clear()

    def _undo(self) -> None:
        self.game.undo()

    def _redo(self) -> None:
        self.game.redo()

    def _flip(self) -> None:
        self.board_widget.flip()

    def _copy_fen(self) -> None:
        QApplication.clipboard().setText(self.game.export_fen())
        self.statusBar().showMessage("当前FEN已复制", 2500)

    def _load_fen(self) -> None:
        fen, accepted = QInputDialog.getMultiLineText(self, "载入FEN", "中国象棋FEN：", self.game.export_fen())
        if not accepted:
            return
        try:
            self.game.load_fen(fen)
        except (ValueError, TypeError) as exc:
            QMessageBox.warning(self, "FEN无效", str(exc))

    def _analyze(self) -> None:
        configured = str(self.store.value("engine/path", "")).strip()
        engine = discover_pikafish(Path(configured) if configured else self.settings.pikafish_path)
        if not engine:
            QMessageBox.information(self, "未配置引擎", "未配置 Pikafish，请在设置中选择 pikafish.exe。")
            return
        if self.engine_thread and self.engine_thread.isRunning():
            self.engine_thread.cancel()
        fen = self.game.export_fen()
        nnue_value = str(self.store.value("engine/nnue", "")).strip()
        self.engine_thread = EngineAnalysisThread(
            executable=engine, nnue=Path(nnue_value) if nnue_value else None, fen=fen,
            threads=int(self.store.value("engine/threads", self.settings.engine_threads)),
            hash_mb=int(self.store.value("engine/hash", self.settings.engine_hash_mb)),
            multipv=int(self.store.value("engine/multipv", self.settings.engine_multipv)),
            depth=int(self.store.value("engine/depth", self.settings.engine_depth)),
            movetime_ms=int(self.store.value("engine/movetime", self.settings.engine_movetime_ms)),
            timeout=self.settings.engine_timeout_seconds,
        )
        self.engine_thread.completed.connect(self._analysis_completed)
        self.engine_thread.failed.connect(lambda message: self.engine_text.setPlainText(f"分析失败：{message}"))
        self.engine_text.setPlainText("正在后台分析当前局面……窗口仍可正常操作。")
        self.actions["分析"].setEnabled(False)
        self.engine_thread.finished.connect(lambda: self.actions["分析"].setEnabled(True))
        self.engine_thread.start()

    def _analysis_completed(self, result: AnalysisResult) -> None:
        if result.fen != self.game.export_fen():
            return
        self.analysis_result = result
        self.candidates.clear()
        lines = [f"深度 {result.depth} · 节点 {result.nodes} · {result.time_ms} ms", f"红方视角评分：{(result.score_for_red or 0)/100:+.2f}"]
        for index, candidate in enumerate(result.candidates, 1):
            move = Move.from_engine(candidate.move)
            chinese = move_to_chinese(self.game.position, move) if move in self.game.position.legal_moves() else candidate.move
            score = "将杀" if candidate.mate is not None else (f"{(candidate.score_for_red or 0)/100:+.2f}")
            self.candidates.addItem(f"{index}. {chinese} ({candidate.move})   {score}")
        self.engine_text.setPlainText("\n".join(lines))
        if result.best_move:
            self.board_widget.recommended_move = Move.from_engine(result.best_move)
            self.board_widget.update()

    def _settings(self) -> None:
        if SettingsDialog(self.settings, self).exec():
            self._show_engine_status()

    def _ask_tutor(self) -> None:
        question = self.question_input.toPlainText().strip()
        if not question:
            return
        base_url = str(self.store.value("ai/base_url", self.settings.llm_base_url)).strip()
        model = str(self.store.value("ai/model", self.settings.llm_model)).strip()
        api_key = keyring.get_password(KEYRING_SERVICE, KEYRING_USER) or ""
        self.tutor_text.append(f"\n你：{question}")
        if not api_key or not model:
            self.tutor_text.append("导师：AI API 尚未配置；这不影响正常下棋和引擎分析。")
            return
        evidence = self._tutor_evidence()
        task = TutorTask.HINT if "提示" in question else TutorTask.FREE_QUESTION
        request = PromptBuilder().build_from_evidence(
            task=task, evidence=evidence, level=UserLevel.INTERMEDIATE, question=question,
            hint_level=HintLevel.HINT_1 if task is TutorTask.HINT else None,
        )
        self.send_button.setEnabled(False)
        self.tutor_thread = TutorThread(
            base_url=base_url, api_key=api_key, model=model,
            temperature=float(self.store.value("ai/temperature", self.settings.llm_temperature)),
            timeout=float(self.store.value("ai/timeout", self.settings.llm_timeout_seconds)), request=request,
        )
        self.tutor_thread.completed.connect(lambda result: self.tutor_text.append(f"导师：{result['content']}"))
        self.tutor_thread.failed.connect(lambda message: self.tutor_text.append(f"导师调用失败：{message}"))
        self.tutor_thread.finished.connect(lambda: self.send_button.setEnabled(True))
        self.tutor_thread.start()

    def _tutor_evidence(self) -> TutorEvidence:
        position = self.game.position
        result = self.analysis_result
        pieces = tuple(EvidencePiece(square.engine, piece.side.value, piece.kind.value) for square, piece in position.pieces())
        candidates = ()
        if result:
            items = []
            for candidate in result.candidates:
                move = Move.from_engine(candidate.move)
                chinese = move_to_chinese(position, move) if move in position.legal_moves() else candidate.move
                items.append(EvidenceCandidate(candidate.move, chinese, candidate.score_for_red, candidate.depth, candidate.pv))
            candidates = tuple(items)
        records = self.game.records
        return TutorEvidence(
            fen=position.to_fen(), side_to_move=position.side_to_move.value, pieces=pieces,
            legal_moves=tuple(move.engine for move in position.legal_moves()),
            recent_moves=tuple(record.chinese for record in records[-8:]),
            last_move=records[-1].move.engine if records else None,
            played_move=records[-1].move.engine if records else None,
            best_move=result.best_move if result else None, candidate_moves=candidates,
            score_for_red=result.score_for_red if result else None,
            pv=result.candidates[0].pv if result and result.candidates else (),
        )

    def _show_engine_status(self) -> None:
        configured = str(self.store.value("engine/path", "")).strip()
        engine = discover_pikafish(Path(configured) if configured else self.settings.pikafish_path)
        network = discover_nnue(engine, self.settings.pikafish_nnue_path)
        if not engine:
            self.engine_text.setPlainText("未检测到 Pikafish。基础下棋、规则、悔棋、FEN仍可正常使用。")
        else:
            self.engine_text.setPlainText(f"已检测到引擎：{engine}\nNNUE：{network or '未检测到'}")

    def _apply_style(self) -> None:
        self.setStyleSheet("""
            QMainWindow { background: #f3f1eb; color: #262521; }
            QToolBar { background: #252724; spacing: 6px; padding: 7px; border: 0; }
            QToolButton { color: #f6f3eb; padding: 7px 9px; }
            QToolButton:disabled { color: #777b75; }
            QTabWidget::pane, QListWidget, QTextEdit { border: 1px solid #d3cec2; background: #fffdf8; }
            QTabBar::tab { padding: 9px 18px; background: #e7e2d8; }
            QTabBar::tab:selected { background: #fffdf8; color: #9e2e25; }
            #turnLabel { font-size: 18px; font-weight: 600; padding: 5px; }
            QPushButton { padding: 7px 10px; }
        """)
