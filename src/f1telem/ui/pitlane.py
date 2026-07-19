"""Panel Pit lane: qué pilotos están AHORA en la calle de boxes, con qué
compuesto entraron, y dos relojes corriendo: tiempo total en la calle y
tiempo detenido (velocidad 0). Ordenado por orden de entrada."""
from __future__ import annotations

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from ..hub import DataHub
from . import theme

ROW_H = 26


def _text_on(bg: QColor) -> QColor:
    lum = 0.299 * bg.redF() + 0.587 * bg.greenF() + 0.114 * bg.blueF()
    return QColor("#111318") if lum > 0.55 else QColor("#ffffff")


class _PitlaneCanvas(QWidget):
    def __init__(self, view: "PitlaneView"):
        super().__init__()
        self.view = view

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self.view._paint(painter, self.width(), self.height())
        painter.end()


class PitlaneView(QWidget):
    def __init__(self, hub: DataHub, parent=None):
        super().__init__(parent)
        self.hub = hub
        # (code, color, compuesto, t_calle, t_detenido) por piloto adentro
        self.rows: list[tuple] = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.canvas = _PitlaneCanvas(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(self.canvas)
        lay.addWidget(scroll)

    def clear_data(self) -> None:
        self.rows = []
        self.canvas.update()

    def refresh(self) -> None:
        hub = self.hub
        now = hub.latest_t
        rows = []
        for drv, visits in hub.pit_lane.items():
            if not visits or visits[-1][2] is not None:
                continue  # nadie adentro (la última visita ya cerró)
            lap, t_in, _ = visits[-1]
            info = hub.drivers.get(drv)
            compound = ""
            tyre_map = hub.tyres.get(drv)
            if tyre_map:
                key = lap if lap in tyre_map else max(
                    (k for k in tyre_map if k <= lap), default=max(tyre_map))
                compound = tyre_map[key][0]
            rows.append((
                info.code if info else drv,
                info.color if info else "#9aa0a6",
                compound,
                max(0.0, now - t_in),
                hub.pit_stationary_time(drv, t_in, now),
                t_in,
            ))
        rows.sort(key=lambda r: r[5])
        self.rows = [r[:5] for r in rows]
        self.canvas.setMinimumHeight(max(len(self.rows) * ROW_H + 8, 40))
        self.canvas.update()

    def _paint(self, p: QPainter, width: int, height: int) -> None:
        f_small = QFont(self.font()); f_small.setPointSizeF(6.5)
        f_code = QFont(self.font()); f_code.setPointSizeF(7.5); f_code.setBold(True)
        f_val = QFont(self.font()); f_val.setPointSizeF(9.0); f_val.setBold(True)
        if not self.rows:
            p.setPen(QColor(theme.TEXT_MUTED))
            p.setFont(f_small)
            p.drawText(QRectF(0, 0, width, min(height, 40)),
                       Qt.AlignCenter, "— pit lane empty —")
            return
        for i, (code, color, compound, lane_s, stop_s) in enumerate(self.rows):
            y = i * ROW_H + 4
            if i % 2:
                p.fillRect(0, y - 2, width, ROW_H, QColor(theme.SURFACE_ALT))
            team = QColor(color)
            p.setPen(Qt.NoPen)
            p.setBrush(team)
            p.drawRoundedRect(QRectF(4, y + 1, 46, ROW_H - 6), 3, 3)
            p.setPen(_text_on(team))
            p.setFont(f_code)
            p.drawText(QRectF(4, y + 1, 46, ROW_H - 6), Qt.AlignCenter, code)
            x = 56
            # compuesto con el que entró
            if compound:
                cc = QColor(theme.COMPOUND_COLORS.get(compound.upper(), "#9aa0a6"))
                d = ROW_H - 10.0
                p.setPen(Qt.NoPen)
                p.setBrush(cc)
                p.drawEllipse(QRectF(x, y + 2, d, d))
                p.setPen(_text_on(cc))
                p.setFont(f_small)
                p.drawText(QRectF(x, y + 2, d, d), Qt.AlignCenter, compound[0])
            x += 24
            # relojes: calle de boxes y detenido
            for label, value in (("PIT", lane_s), ("STOP", stop_s)):
                p.setPen(QColor(theme.TEXT_MUTED))
                p.setFont(f_small)
                p.drawText(QRectF(x, y - 1, 34, ROW_H - 4),
                           Qt.AlignVCenter | Qt.AlignRight, label)
                p.setPen(QColor(theme.TEXT))
                p.setFont(f_val)
                p.drawText(QRectF(x + 38, y - 1, 52, ROW_H - 4),
                           Qt.AlignVCenter | Qt.AlignLeft, f"{value:.1f}s")
                x += 96
