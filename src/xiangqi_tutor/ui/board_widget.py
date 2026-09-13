from __future__ import annotations

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from xiangqi_tutor.board import PieceType
from xiangqi_tutor.models.core import Move, Side, Square
from xiangqi_tutor.services import GameService

PIECE_TEXT = {
    (Side.RED, PieceType.GENERAL): "帅",
    (Side.BLACK, PieceType.GENERAL): "将",
    (Side.RED, PieceType.ADVISOR): "仕",
    (Side.BLACK, PieceType.ADVISOR): "士",
    (Side.RED, PieceType.ELEPHANT): "相",
    (Side.BLACK, PieceType.ELEPHANT): "象",
    (Side.RED, PieceType.HORSE): "马",
    (Side.BLACK, PieceType.HORSE): "马",
    (Side.RED, PieceType.ROOK): "车",
    (Side.BLACK, PieceType.ROOK): "车",
    (Side.RED, PieceType.CANNON): "炮",
    (Side.BLACK, PieceType.CANNON): "炮",
    (Side.RED, PieceType.PAWN): "兵",
    (Side.BLACK, PieceType.PAWN): "卒",
}


class XiangqiBoardWidget(QWidget):
    move_attempted = Signal(object)

    def __init__(self, game: GameService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.game = game
        self.selected: Square | None = None
        self.flipped = False
        self.recommended_move: Move | None = None
        self.visual_arrows: tuple[tuple[Move, str], ...] = ()
        self.visual_highlights: tuple[tuple[Square, str], ...] = ()
        self.input_enabled = True
        self.setMinimumSize(480, 540)
        self.setMouseTracking(True)
        game.position_changed.connect(self._position_changed)

    def _geometry(self) -> tuple[float, float, float]:
        cell = min((self.width() - 56) / 8, (self.height() - 56) / 9)
        return (self.width() - cell * 8) / 2, (self.height() - cell * 9) / 2, cell

    def _screen_point(self, square: Square) -> QPointF:
        left, top, cell = self._geometry()
        col = square.file if self.flipped else 8 - square.file
        row = square.rank if self.flipped else 9 - square.rank
        return QPointF(left + col * cell, top + row * cell)

    def square_at(self, point: QPointF) -> Square | None:
        left, top, cell = self._geometry()
        col = round((point.x() - left) / cell)
        row = round((point.y() - top) / cell)
        if not 0 <= col < 9 or not 0 <= row < 10:
            return None
        file = col if self.flipped else 8 - col
        rank = row if self.flipped else 9 - row
        return Square(file, rank)

    def flip(self) -> None:
        self.flipped = not self.flipped
        self.selected = None
        self.update()

    def _position_changed(self, _position) -> None:
        self.selected = None
        self.recommended_move = None
        self.visual_arrows = ()
        self.visual_highlights = ()
        self.update()

    def set_teaching_visuals(self, arrows: tuple[tuple[Move, str], ...], highlights: tuple[tuple[Square, str], ...]) -> None:
        self.visual_arrows = arrows
        self.visual_highlights = highlights
        self.update()

    def mousePressEvent(self, event) -> None:
        if not self.input_enabled:
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        square = self.square_at(event.position())
        if square is None:
            self.selected = None
            self.update()
            return
        piece = self.game.position.piece_at(square)
        if self.selected is not None and square in self.game.legal_targets(self.selected):
            move = Move(self.selected, square)
            self.move_attempted.emit(move)
            self.selected = None
        elif piece and piece.side is self.game.position.side_to_move:
            self.selected = square
        else:
            self.selected = None
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f6f2e8"))
        left, top, cell = self._geometry()
        board_rect = QRectF(left - cell * 0.42, top - cell * 0.42, cell * 8.84, cell * 9.84)
        painter.fillRect(board_rect, QColor("#dfbd7c"))
        painter.setPen(QPen(QColor("#3c2b1f"), max(1.2, cell * 0.018)))
        for row in range(10):
            y = top + row * cell
            painter.drawLine(QPointF(left, y), QPointF(left + 8 * cell, y))
        for col in range(9):
            x = left + col * cell
            if col in (0, 8):
                painter.drawLine(QPointF(x, top), QPointF(x, top + 9 * cell))
            else:
                painter.drawLine(QPointF(x, top), QPointF(x, top + 4 * cell))
                painter.drawLine(QPointF(x, top + 5 * cell), QPointF(x, top + 9 * cell))
        for top_row in (0, 7):
            painter.drawLine(QPointF(left + 3 * cell, top + top_row * cell), QPointF(left + 5 * cell, top + (top_row + 2) * cell))
            painter.drawLine(QPointF(left + 5 * cell, top + top_row * cell), QPointF(left + 3 * cell, top + (top_row + 2) * cell))
        painter.setPen(QColor("#6f3b26"))
        painter.setFont(QFont("Microsoft YaHei UI", max(12, int(cell * 0.3)), QFont.Weight.Bold))
        painter.drawText(QRectF(left, top + 4 * cell, 4 * cell, cell), Qt.AlignmentFlag.AlignCenter, "楚 河")
        painter.drawText(QRectF(left + 4 * cell, top + 4 * cell, 4 * cell, cell), Qt.AlignmentFlag.AlignCenter, "汉 界")

        for square, kind in self.visual_highlights:
            point = self._screen_point(square)
            color = QColor(220, 55, 45, 95) if kind == "danger" else QColor(245, 190, 35, 110)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRect(QRectF(point.x() - cell * 0.43, point.y() - cell * 0.43, cell * 0.86, cell * 0.86))

        arrows = list(self.visual_arrows)
        if self.recommended_move:
            arrows.append((self.recommended_move, "recommended"))
        for arrow, kind in arrows:
            source = self._screen_point(arrow.source)
            target = self._screen_point(arrow.target)
            line = QLineF(source, target)
            if line.length() > 0:
                unit = QLineF.fromPolar(cell * 0.22, line.angle() + 150)
                other = QLineF.fromPolar(cell * 0.22, line.angle() - 150)
                color = QColor(200, 48, 42, 205) if kind == "danger" else QColor(32, 126, 90, 205)
                style = Qt.PenStyle.DashLine if kind == "plan" else Qt.PenStyle.SolidLine
                painter.setBrush(color)
                painter.setPen(QPen(color, max(4, cell * 0.08), style, Qt.PenCapStyle.RoundCap))
                painter.drawLine(line)
                painter.drawPolygon(QPolygonF([target, target + unit.p2(), target + other.p2()]))

        last = self.game.records[-1].move if self.game.records else None
        for square, piece in self.game.position.pieces():
            center = self._screen_point(square)
            radius = cell * 0.39
            if last and square in (last.source, last.target):
                painter.setBrush(QColor(255, 215, 80, 135))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(center, radius * 1.15, radius * 1.15)
            painter.setBrush(QColor("#f8e7bd"))
            color = QColor("#b12c24") if piece.side is Side.RED else QColor("#20201e")
            painter.setPen(QPen(color, max(2, cell * 0.04)))
            painter.drawEllipse(center, radius, radius)
            painter.setPen(color)
            painter.setFont(QFont("Microsoft YaHei UI", max(14, int(cell * 0.43)), QFont.Weight.Bold))
            painter.drawText(
                QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2),
                Qt.AlignmentFlag.AlignCenter,
                PIECE_TEXT[(piece.side, piece.kind)],
            )

        if self.selected:
            center = self._screen_point(self.selected)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor("#1d7f5f"), max(3, cell * 0.06)))
            painter.drawEllipse(center, cell * 0.46, cell * 0.46)
            painter.setBrush(QColor(30, 140, 95, 155))
            painter.setPen(Qt.PenStyle.NoPen)
            for target in self.game.legal_targets(self.selected):
                point = self._screen_point(target)
                painter.drawEllipse(point, cell * 0.11, cell * 0.11)
        if self.game.position.is_in_check(self.game.position.side_to_move):
            general = self.game.position.general_square(self.game.position.side_to_move)
            if general:
                point = self._screen_point(general)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QColor("#d02020"), max(4, cell * 0.08)))
                painter.drawEllipse(point, cell * 0.49, cell * 0.49)
