from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

import keyring
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from xiangqi_tutor.board import IllegalMoveError
from xiangqi_tutor.config import AppSettings
from xiangqi_tutor.database.connection import Database
from xiangqi_tutor.engine import EngineJob, EngineJobFailure, EngineJobResult, EngineManager, PVValidator
from xiangqi_tutor.engine.discovery import discover_nnue, discover_pikafish
from xiangqi_tutor.models.core import Move, Side, Square
from xiangqi_tutor.models.engine import AnalysisResult
from xiangqi_tutor.notation import move_to_chinese
from xiangqi_tutor.services import EngineMoveRequest, GameMode, MatchService, MatchState, MoveAssessment, MoveAssessmentService
from xiangqi_tutor.tutor import (
    EvidenceCandidate,
    EvidencePiece,
    EvidencePVStep,
    HintLevel,
    PromptBuilder,
    TutorEvidence,
    TutorResponse,
    TutorTask,
    UserLevel,
)
from xiangqi_tutor.ui.board_widget import XiangqiBoardWidget
from xiangqi_tutor.ui.new_match_dialog import NewMatchDialog
from xiangqi_tutor.ui.settings_dialog import KEYRING_SERVICE, KEYRING_USER, SettingsDialog
from xiangqi_tutor.ui.workers import TutorThread


class MainWindow(QMainWindow):
    def __init__(self, settings: AppSettings, database: Database) -> None:
        super().__init__()
        self.settings = settings
        self.database = database
        self.match = MatchService()
        self.game = self.match.game
        self.store = QSettings("XiangqiTutor", "XiangqiTutor")
        self.analysis_result: AnalysisResult | None = None
        self.engine_manager: EngineManager | None = None
        self.engine_signature: tuple | None = None
        self.analysis_job_id: str | None = None
        self.baseline_job_id: str | None = None
        self.baseline_analysis: AnalysisResult | None = None
        self.pending_assessment: tuple[AnalysisResult, str] | None = None
        self.latest_assessment: MoveAssessment | None = None
        self.assessment_service = MoveAssessmentService()
        self.tutor_thread: TutorThread | None = None
        self.selected_tutor_task: TutorTask | None = None
        self.hint_index = 0
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
        quick_tasks = (
            ("为什么推荐？", TutorTask.EXPLAIN_MOVE),
            ("这步有何问题？", TutorTask.EXPLAIN_MOVE),
            ("比较候选", TutorTask.COMPARE_MOVES),
            ("只给提示", TutorTask.HINT),
        )
        for text, task in quick_tasks:
            button = QPushButton(text)
            button.clicked.connect(lambda checked=False, value=text, selected=task: self._choose_tutor_task(value, selected))
            quick.addWidget(button)
        self.more_hint_button = QPushButton("再给一点提示")
        self.more_hint_button.clicked.connect(self._next_hint)
        self.send_button = QPushButton("发送给导师")
        self.send_button.clicked.connect(lambda: self._ask_tutor())
        tutor_layout.addWidget(self.tutor_text, 1)
        tutor_layout.addLayout(quick)
        tutor_layout.addWidget(self.more_hint_button)
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
        self.game.repetition_detected.connect(lambda message: self.statusBar().showMessage(message, 6000))
        self.match.state_changed.connect(self._match_state_changed)
        self.match.engine_move_requested.connect(self._request_engine_move)
        self.match.engine_request_cancelled.connect(self._cancel_engine_job)
        self.match.engine_error.connect(lambda message: QMessageBox.warning(self, "电脑走棋失败", message))

    def _make_move(self, move: Move) -> None:
        try:
            before = self.baseline_analysis if self.baseline_analysis and self.baseline_analysis.fen == self.game.export_fen() else None
            if self.baseline_job_id and self.engine_manager:
                self.engine_manager.cancel(self.baseline_job_id)
                self.baseline_job_id = None
            self.pending_assessment = (before, move.engine) if before and self.match.mode is GameMode.HUMAN_VS_ENGINE else None
            self.match.make_human_move(move)
        except (IllegalMoveError, ValueError) as exc:
            self.pending_assessment = None
            self.statusBar().showMessage(str(exc), 3000)

    def _refresh_position(self) -> None:
        if self.analysis_job_id and self.engine_manager:
            self.engine_manager.cancel(self.analysis_job_id)
            self.analysis_job_id = None
            self.actions["分析"].setEnabled(True)
        self.analysis_result = None
        self.baseline_analysis = None
        self.hint_index = 0
        self.selected_tutor_task = None
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
                black = f"    {records[index + 1].chinese} ({records[index + 1].move.engine})"
            self.history.addItem(f"{index // 2 + 1}. {red}{black}")
        self.actions["悔棋"].setEnabled(bool(records))
        self.actions["重做"].setEnabled(self.game.can_redo)
        self.board_widget.update()
        self._match_state_changed(self.match.state)

    def _match_state_changed(self, state: MatchState) -> None:
        mode = {
            GameMode.HUMAN_VS_ENGINE: "人机对弈",
            GameMode.HUMAN_VS_HUMAN: "双人对弈",
            GameMode.ANALYSIS: "分析模式",
        }[self.match.mode]
        owner = ""
        if self.match.mode is GameMode.HUMAN_VS_ENGINE:
            owner = f" · 我方{'红' if self.match.human_side is Side.RED else '黑'}"
        if state is MatchState.ENGINE_THINKING:
            message = "电脑正在思考……"
        elif state is MatchState.GAME_OVER:
            message = "对局结束"
        else:
            message = "轮到你" if self.match.can_human_move else "等待操作"
        self.board_widget.input_enabled = self.match.can_human_move
        self.statusBar().showMessage(f"{mode}{owner} · {message}")

    def _configured_engine_path(self) -> Path | None:
        configured = str(self.store.value("engine/path", "")).strip()
        return discover_pikafish(Path(configured) if configured else self.settings.pikafish_path)

    def _ensure_engine_manager(self) -> EngineManager | None:
        engine = self._configured_engine_path()
        if not engine:
            return None
        nnue_value = str(self.store.value("engine/nnue", "")).strip()
        nnue = Path(nnue_value) if nnue_value else None
        signature = (
            engine,
            nnue,
            int(self.store.value("engine/threads", self.settings.engine_threads)),
            int(self.store.value("engine/hash", self.settings.engine_hash_mb)),
            self.settings.engine_timeout_seconds,
        )
        if self.engine_manager and self.engine_signature != signature:
            self.engine_manager.close()
            self.engine_manager = None
        if self.engine_manager is None:
            self.engine_manager = EngineManager(
                engine,
                nnue=nnue,
                threads=signature[2],
                hash_mb=signature[3],
                timeout=signature[4],
                database=self.database,
            )
            self.engine_manager.completed.connect(self._engine_job_completed)
            self.engine_manager.failed.connect(self._engine_job_failed)
            self.engine_signature = signature
        return self.engine_manager

    def _request_engine_move(self, request: EngineMoveRequest) -> None:
        manager = self._ensure_engine_manager()
        if not manager:
            self.match.engine_failed(request.request_id, "未配置Pikafish")
            return
        manager.submit(
            EngineJob(
                request.request_id,
                request.fen,
                request.position_version,
                request.depth,
                request.movetime_ms,
                multipv=1,
            )
        )

    def _cancel_engine_job(self, request_id: str) -> None:
        if self.engine_manager:
            self.engine_manager.cancel(request_id)

    def _engine_job_completed(self, result: EngineJobResult) -> None:
        if result.job.request_id == self.baseline_job_id:
            self.baseline_job_id = None
            if result.job.fen == self.game.export_fen() and result.job.position_version == self.match.position_version:
                self.baseline_analysis = result.analysis
            return
        if result.job.request_id == self.analysis_job_id:
            self.analysis_job_id = None
            self.actions["分析"].setEnabled(True)
            self._analysis_completed(result.analysis)
            return
        if result.analysis.best_move:
            if self.pending_assessment and self.pending_assessment[0].fen != result.analysis.fen:
                self.pending_assessment = None
            if self.pending_assessment:
                before, played = self.pending_assessment
                try:
                    self.latest_assessment = self.assessment_service.assess(
                        before=before,
                        after=result.analysis,
                        played_move=played,
                        user_side=self.match.human_side,
                    )
                    self._show_assessment(self.latest_assessment)
                except ValueError:
                    self.latest_assessment = None
                self.pending_assessment = None
            applied = self.match.apply_engine_move(
                result.job.request_id,
                result.job.fen,
                result.job.position_version,
                result.analysis.best_move,
            )
            if applied:
                self._request_baseline_analysis()
        else:
            self.match.engine_failed(result.job.request_id, "Pikafish没有返回合法走法")

    def _engine_job_failed(self, failure: EngineJobFailure) -> None:
        if failure.job.request_id == self.baseline_job_id:
            self.baseline_job_id = None
            return
        if failure.job.request_id == self.analysis_job_id:
            self.analysis_job_id = None
            self.actions["分析"].setEnabled(True)
            self.engine_text.setPlainText(f"分析失败：{failure.message}")
        else:
            self.match.engine_failed(failure.job.request_id, failure.message)

    def _request_baseline_analysis(self) -> None:
        if self.match.mode is not GameMode.HUMAN_VS_ENGINE or not self.match.can_human_move:
            return
        manager = self._ensure_engine_manager()
        if not manager:
            return
        self.baseline_job_id = str(uuid4())
        depth, movetime = self.match.strength.limits
        manager.submit(
            EngineJob(
                self.baseline_job_id,
                self.game.export_fen(),
                self.match.position_version,
                depth,
                movetime,
                multipv=max(3, int(self.store.value("engine/multipv", self.settings.engine_multipv))),
            )
        )

    def _show_assessment(self, assessment: MoveAssessment) -> None:
        labels = {
            "best": "最佳",
            "excellent": "优秀",
            "good": "良好",
            "inaccuracy": "不精确",
            "mistake": "失误",
            "blunder": "严重失误",
        }
        loss = "无法量化" if assessment.evaluation_loss is None else f"{assessment.evaluation_loss / 100:.2f}兵"
        self.tutor_text.append(
            f"\n走法评价：{labels[assessment.grade.value]} · {assessment.played_move} · 用户视角损失 {loss}\n"
            f"对手最强回应：{assessment.opponent_best_reply or '引擎未返回'}"
        )

    def _new_game(self) -> None:
        dialog = NewMatchDialog(self)
        if not dialog.exec():
            return
        if dialog.mode is GameMode.HUMAN_VS_ENGINE and not self._configured_engine_path():
            QMessageBox.information(self, "需要Pikafish", "人机对弈需要先在设置中选择可运行的 pikafish.exe。基础双人和分析模式仍可使用。")
            return
        self.match.new_match(dialog.mode, dialog.human_side, dialog.strength)
        if dialog.mode is GameMode.HUMAN_VS_ENGINE:
            self.board_widget.flipped = dialog.human_side is Side.BLACK
            self.board_widget.update()
        if self.match.can_human_move:
            self._request_baseline_analysis()
        self.candidates.clear()

    def _undo(self) -> None:
        self.match.undo_decision()
        self.pending_assessment = None
        self._request_baseline_analysis()

    def _redo(self) -> None:
        self.match.redo_decision()
        self.pending_assessment = None
        self._request_baseline_analysis()

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
        manager = self._ensure_engine_manager()
        if not manager:
            QMessageBox.information(self, "未配置引擎", "未配置 Pikafish，请在设置中选择 pikafish.exe。")
            return
        fen = self.game.export_fen()
        if self.analysis_job_id:
            manager.cancel(self.analysis_job_id)
        self.analysis_job_id = str(uuid4())
        self.engine_text.setPlainText("正在后台分析当前局面……窗口仍可正常操作。")
        self.actions["分析"].setEnabled(False)
        manager.submit(
            EngineJob(
                self.analysis_job_id,
                fen,
                self.match.position_version,
                int(self.store.value("engine/depth", self.settings.engine_depth)),
                int(self.store.value("engine/movetime", self.settings.engine_movetime_ms)),
                int(self.store.value("engine/multipv", self.settings.engine_multipv)),
            )
        )

    def _analysis_completed(self, result: AnalysisResult) -> None:
        if result.fen != self.game.export_fen():
            return
        self.analysis_result = result
        self.candidates.clear()
        if result.candidates and result.candidates[0].evaluation and result.candidates[0].mate is not None:
            score_text = result.candidates[0].evaluation.for_red_text()
        elif result.score_for_red is None:
            score_text = "暂无有效评分"
        else:
            score_text = f"{result.score_for_red / 100:+.2f}"
        lines = [f"深度 {result.depth} · 节点 {result.nodes} · {result.time_ms} ms", f"红方视角评分：{score_text}"]
        for index, candidate in enumerate(result.candidates, 1):
            move = Move.from_engine(candidate.move)
            chinese = move_to_chinese(self.game.position, move) if move in self.game.position.legal_moves() else candidate.move
            if candidate.evaluation:
                score = candidate.evaluation.for_red_text()
            elif candidate.score_for_red is not None:
                score = f"{candidate.score_for_red / 100:+.2f}"
            else:
                score = "暂无评分"
            self.candidates.addItem(f"{index}. {chinese} ({candidate.move})   {score}")
        self.engine_text.setPlainText("\n".join(lines))
        if result.best_move:
            self.board_widget.recommended_move = Move.from_engine(result.best_move)
            self.board_widget.update()

    def _settings(self) -> None:
        if SettingsDialog(self.settings, self).exec():
            self._show_engine_status()

    def _choose_tutor_task(self, question: str, task: TutorTask) -> None:
        self.question_input.setPlainText(question)
        self.selected_tutor_task = task

    def _next_hint(self) -> None:
        self.hint_index = min(self.hint_index + 1, 3)
        self.selected_tutor_task = TutorTask.HINT
        self.question_input.setPlainText("请再给我一点提示" if self.hint_index < 3 else "请公布答案并解释")
        self._ask_tutor(TutorTask.HINT)

    def _route_tutor_task(self, question: str) -> TutorTask:
        if self.selected_tutor_task:
            return self.selected_tutor_task
        if "提示" in question:
            return TutorTask.HINT
        if "比较" in question or "候选" in question:
            return TutorTask.COMPARE_MOVES
        if "复盘" in question:
            return TutorTask.REVIEW_GAME
        if "为什么" in question or "问题" in question or "不好" in question:
            return TutorTask.EXPLAIN_MOVE
        return TutorTask.FREE_QUESTION

    def _ask_tutor(self, forced_task: TutorTask | None = None) -> None:
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
        task = forced_task or self._route_tutor_task(question)
        hint_levels = (HintLevel.HINT_1, HintLevel.HINT_2, HintLevel.HINT_3, HintLevel.ANSWER)
        hint_level = hint_levels[self.hint_index] if task is TutorTask.HINT else None
        request_fen = self.game.export_fen()
        request_version = self.match.position_version
        request = PromptBuilder().build_from_evidence(
            task=task,
            evidence=evidence,
            level=UserLevel.INTERMEDIATE,
            question=question,
            hint_level=hint_level,
            request_visuals=True,
        )
        self.send_button.setEnabled(False)
        self.tutor_thread = TutorThread(
            base_url=base_url,
            api_key=api_key,
            model=model,
            temperature=float(self.store.value("ai/temperature", self.settings.llm_temperature)),
            timeout=float(self.store.value("ai/timeout", self.settings.llm_timeout_seconds)),
            request=request,
            database=self.database,
            cache_key=hashlib.sha256(f"v2|{model}|{task.value}|{question}|{request.context['user_prompt']}".encode("utf-8")).hexdigest(),
            fen=request_fen,
        )
        self.tutor_thread.completed.connect(lambda result: self._tutor_completed(result, request_fen, request_version, task))
        self.tutor_thread.failed.connect(lambda message: self.tutor_text.append(f"导师调用失败：{message}"))
        self.tutor_thread.finished.connect(lambda: self.send_button.setEnabled(True))
        self.tutor_thread.start()

    def _tutor_completed(self, result: dict[str, object], fen: str, version: int, task: TutorTask) -> None:
        response = TutorResponse.parse_text(str(result.get("content", "")))
        text = response.summary
        if response.explanation:
            text += ("\n" if text else "") + response.explanation
        if response.lesson:
            text += f"\n你应该记住：{response.lesson}"
        stale = fen != self.game.export_fen() or version != self.match.position_version
        marker = "（以下解释针对上一局面）\n" if stale else ""
        self.tutor_text.append(f"导师 [{task.value}]：{marker}{text}")
        if not stale:
            arrows = tuple((Move.from_engine(item.source + item.target), item.type) for item in response.arrows)
            highlights = tuple((Square.from_engine(item.square), item.type) for item in response.highlights)
            self.board_widget.set_teaching_visuals(arrows, highlights)

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
                items.append(
                    EvidenceCandidate(
                        candidate.move,
                        chinese,
                        candidate.score_for_red,
                        candidate.depth,
                        candidate.pv,
                        candidate.evaluation.kind.value if candidate.evaluation else None,
                        candidate.mate,
                    )
                )
            candidates = tuple(items)
        records = self.game.records
        validated = ()
        if result and result.candidates:
            validated = tuple(
                EvidencePVStep(step.move, step.chinese, step.fen_before, step.fen_after, step.side.value)
                for step in PVValidator.validate(position, result.candidates[0].pv)
            )
        return TutorEvidence(
            fen=position.to_fen(),
            side_to_move=position.side_to_move.value,
            pieces=pieces,
            legal_moves=tuple(move.engine for move in position.legal_moves()),
            recent_moves=tuple(record.chinese for record in records[-8:]),
            last_move=records[-1].move.engine if records else None,
            played_move=records[-1].move.engine if records else None,
            best_move=result.best_move if result else None,
            candidate_moves=candidates,
            score_for_red=result.score_for_red if result else None,
            pv=result.candidates[0].pv if result and result.candidates else (),
            validated_pv=validated,
            request_id=str(uuid4()),
            position_version=self.match.position_version,
        )

    def _show_engine_status(self) -> None:
        configured = str(self.store.value("engine/path", "")).strip()
        engine = discover_pikafish(Path(configured) if configured else self.settings.pikafish_path)
        network = discover_nnue(engine, self.settings.pikafish_nnue_path)
        if not engine:
            self.engine_text.setPlainText("未检测到 Pikafish。基础下棋、规则、悔棋、FEN仍可正常使用。")
        else:
            self.engine_text.setPlainText(f"已检测到引擎：{engine}\nNNUE：{network or '未检测到'}")

    def closeEvent(self, event) -> None:
        if self.analysis_job_id and self.engine_manager:
            self.engine_manager.cancel(self.analysis_job_id)
        if self.baseline_job_id and self.engine_manager:
            self.engine_manager.cancel(self.baseline_job_id)
        self.match.cancel_engine_request()
        if self.engine_manager:
            self.engine_manager.close()
            self.engine_manager = None
        if self.tutor_thread and self.tutor_thread.isRunning():
            self.tutor_thread.requestInterruption()
            self.tutor_thread.wait(int(self.settings.llm_timeout_seconds * 1000) + 1000)
        super().closeEvent(event)

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
