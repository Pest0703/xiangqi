from __future__ import annotations

import keyring
from PySide6.QtCore import QSettings
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

from xiangqi_tutor.board import START_FEN
from xiangqi_tutor.config import AppSettings
from xiangqi_tutor.tutor.provider import TutorRequest
from xiangqi_tutor.ui.workers import EngineAnalysisThread, TutorThread

KEYRING_SERVICE = "xiangqi-tutor"
KEYRING_USER = "llm-api-key"


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.store = QSettings("XiangqiTutor", "XiangqiTutor")
        self.setWindowTitle("设置")
        self.resize(620, 420)
        self.engine_test_thread: EngineAnalysisThread | None = None
        self.ai_test_thread: TutorThread | None = None
        tabs = QTabWidget()
        tabs.addTab(self._engine_page(), "Pikafish")
        tabs.addTab(self._ai_page(), "AI导师")
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

    def _path_row(self, edit: QLineEdit, title: str) -> QWidget:
        container = QWidget(); layout = QHBoxLayout(container); layout.setContentsMargins(0,0,0,0)
        button = QPushButton("浏览…")
        button.clicked.connect(lambda: (lambda path: edit.setText(path) if path else None)(QFileDialog.getOpenFileName(self, title)[0]))
        layout.addWidget(edit, 1); layout.addWidget(button)
        return container

    def _engine_page(self) -> QWidget:
        page = QWidget(); form = QFormLayout(page)
        self.engine_path = QLineEdit(str(self.settings.pikafish_path or self.store.value("engine/path", "")))
        self.nnue_path = QLineEdit(str(self.settings.pikafish_nnue_path or self.store.value("engine/nnue", "")))
        self.threads = QSpinBox(); self.threads.setRange(1, 128); self.threads.setValue(int(self.store.value("engine/threads", self.settings.engine_threads)))
        self.hash_mb = QSpinBox(); self.hash_mb.setRange(16, 65536); self.hash_mb.setValue(int(self.store.value("engine/hash", self.settings.engine_hash_mb)))
        self.multipv = QSpinBox(); self.multipv.setRange(1, 10); self.multipv.setValue(int(self.store.value("engine/multipv", self.settings.engine_multipv)))
        self.depth = QSpinBox(); self.depth.setRange(1, 100); self.depth.setValue(int(self.store.value("engine/depth", self.settings.engine_depth)))
        self.movetime = QSpinBox(); self.movetime.setRange(100, 600000); self.movetime.setValue(int(self.store.value("engine/movetime", self.settings.engine_movetime_ms)))
        form.addRow("Pikafish 可执行文件", self._path_row(self.engine_path, "选择 pikafish.exe"))
        form.addRow("NNUE 文件", self._path_row(self.nnue_path, "选择 NNUE"))
        for label, widget in (("Threads",self.threads),("Hash (MB)",self.hash_mb),("MultiPV",self.multipv),("Depth",self.depth),("MoveTime (ms)",self.movetime)): form.addRow(label, widget)
        self.engine_test_status = QLabel()
        self.engine_test_button = QPushButton("测试引擎")
        self.engine_test_button.clicked.connect(self._test_engine)
        form.addRow(self.engine_test_button, self.engine_test_status)
        return page

    def _ai_page(self) -> QWidget:
        page = QWidget(); form = QFormLayout(page)
        self.base_url = QLineEdit(str(self.store.value("ai/base_url", self.settings.llm_base_url)))
        self.api_key = QLineEdit(); self.api_key.setEchoMode(QLineEdit.EchoMode.Password); self.api_key.setPlaceholderText("留空则保留 Windows 凭据库中的现有密钥")
        self.model = QLineEdit(str(self.store.value("ai/model", self.settings.llm_model)))
        self.temperature = QDoubleSpinBox(); self.temperature.setRange(0,2); self.temperature.setSingleStep(.1); self.temperature.setValue(float(self.store.value("ai/temperature", self.settings.llm_temperature)))
        self.ai_timeout = QSpinBox(); self.ai_timeout.setRange(1,300); self.ai_timeout.setValue(int(self.store.value("ai/timeout", self.settings.llm_timeout_seconds)))
        for label, widget in (("API Base URL",self.base_url),("API Key",self.api_key),("Model",self.model),("Temperature",self.temperature),("Timeout (s)",self.ai_timeout)): form.addRow(label, widget)
        self.ai_test_status = QLabel()
        self.ai_test_button = QPushButton("测试连接")
        self.ai_test_button.clicked.connect(self._test_ai)
        form.addRow(self.ai_test_button, self.ai_test_status)
        return page

    def _test_engine(self) -> None:
        path = Path(self.engine_path.text().strip())
        if not path.is_file():
            self.engine_test_status.setText("路径不存在")
            return
        self.engine_test_button.setEnabled(False)
        self.engine_test_status.setText("正在连接……")
        nnue = Path(self.nnue_path.text().strip()) if self.nnue_path.text().strip() else None
        self.engine_test_thread = EngineAnalysisThread(
            executable=path, nnue=nnue, fen=START_FEN, threads=self.threads.value(),
            hash_mb=self.hash_mb.value(), multipv=self.multipv.value(), depth=1,
            movetime_ms=100, timeout=10,
        )
        self.engine_test_thread.completed.connect(lambda _: self.engine_test_status.setText("连接成功"))
        self.engine_test_thread.failed.connect(lambda message: self.engine_test_status.setText(f"连接失败：{message}"))
        self.engine_test_thread.finished.connect(lambda: self.engine_test_button.setEnabled(True))
        self.engine_test_thread.start()

    def _test_ai(self) -> None:
        api_key = self.api_key.text().strip() or keyring.get_password(KEYRING_SERVICE, KEYRING_USER) or ""
        if not api_key:
            self.ai_test_status.setText("请先输入 API Key")
            return
        self.ai_test_button.setEnabled(False)
        self.ai_test_status.setText("正在连接……")
        request = TutorRequest(task="connection_test", context={"system_prompt": "你只需回复 OK。", "user_prompt": "连接测试"})
        self.ai_test_thread = TutorThread(
            base_url=self.base_url.text().strip(), api_key=api_key,
            model=self.model.text().strip(), temperature=self.temperature.value(),
            timeout=float(self.ai_timeout.value()), request=request,
        )
        self.ai_test_thread.completed.connect(lambda _: self.ai_test_status.setText("连接成功"))
        self.ai_test_thread.failed.connect(lambda message: self.ai_test_status.setText(f"连接失败：{message}"))
        self.ai_test_thread.finished.connect(lambda: self.ai_test_button.setEnabled(True))
        self.ai_test_thread.start()

    def _save(self) -> None:
        values = {
            "engine/path":self.engine_path.text().strip(), "engine/nnue":self.nnue_path.text().strip(),
            "engine/threads":self.threads.value(), "engine/hash":self.hash_mb.value(), "engine/multipv":self.multipv.value(),
            "engine/depth":self.depth.value(), "engine/movetime":self.movetime.value(),
            "ai/base_url":self.base_url.text().strip(), "ai/model":self.model.text().strip(),
            "ai/temperature":self.temperature.value(), "ai/timeout":self.ai_timeout.value(),
        }
        for key, value in values.items(): self.store.setValue(key, value)
        if self.api_key.text().strip(): keyring.set_password(KEYRING_SERVICE, KEYRING_USER, self.api_key.text().strip())
        self.accept()
