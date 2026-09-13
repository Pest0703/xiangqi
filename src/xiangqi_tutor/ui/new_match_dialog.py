from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QVBoxLayout

from xiangqi_tutor.models.core import Side
from xiangqi_tutor.services import EngineStrength, GameMode


class NewMatchDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("新对局")
        self.mode_box = QComboBox()
        self.mode_box.addItem("人机对弈", GameMode.HUMAN_VS_ENGINE)
        self.mode_box.addItem("双人对弈", GameMode.HUMAN_VS_HUMAN)
        self.mode_box.addItem("分析模式", GameMode.ANALYSIS)
        self.side_box = QComboBox()
        self.side_box.addItem("红方", Side.RED)
        self.side_box.addItem("黑方", Side.BLACK)
        self.strength_box = QComboBox()
        for label, strength in (
            ("休闲", EngineStrength.CASUAL),
            ("标准", EngineStrength.STANDARD),
            ("强", EngineStrength.STRONG),
            ("最高", EngineStrength.MAXIMUM),
        ):
            self.strength_box.addItem(label, strength)
        self.mode_box.currentIndexChanged.connect(self._mode_changed)
        form = QFormLayout()
        form.addRow("对局模式", self.mode_box)
        form.addRow("我执", self.side_box)
        form.addRow("AI强度", self.strength_box)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _mode_changed(self) -> None:
        enabled = self.mode is GameMode.HUMAN_VS_ENGINE
        self.side_box.setEnabled(enabled)
        self.strength_box.setEnabled(enabled)

    @property
    def mode(self) -> GameMode:
        return self.mode_box.currentData()

    @property
    def human_side(self) -> Side:
        return self.side_box.currentData()

    @property
    def strength(self) -> EngineStrength:
        return self.strength_box.currentData()
