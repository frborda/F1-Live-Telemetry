"""Reproductor de importación: toma una captura .jsonl grabada y la re-emite
a un archivo de salida NUEVO como si el stream estuviera llegando en vivo.

Modelo idéntico al vivo real: el historial desde el inicio de la carrera
hasta el punto de arranque elegido se vuelca INSTANTÁNEAMENTE (la app
principal siempre recibe el panorama completo, igual que cuando engancha una
captura en curso), y desde ahí las líneas salen cronológicamente a ritmo
real (x1), sin pausa ni retroceso. El visualizador sigue el archivo con su
fuente "Capture" y no distingue datos reales de importados.
"""
from __future__ import annotations

import json
import time

from PySide6.QtCore import Signal

from .base import BaseSource
from .live import _parse_utc


def parse_hms(text: str) -> float | None:
    """'hh:mm:ss' (o 'mm:ss', o segundos) -> segundos; None si no parsea."""
    parts = (text or "").strip().split(":")
    if not parts or len(parts) > 3:
        return None
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        return None
    if any(n < 0 for n in nums):
        return None
    secs = 0.0
    for n in nums:
        secs = secs * 60.0 + n
    return secs


def _line_time(raw: bytes) -> float | None:
    """Instante (epoch) de una línea del envoltorio SignalR, tomado del stamp
    A[2] de cada feed; None si la línea no lo trae (p. ej. el snapshot R)."""
    try:
        msg = json.loads(raw)
    except ValueError:
        return None
    latest = None
    for item in msg.get("M", []) or []:
        args = item.get("A") or []
        if len(args) >= 3 and isinstance(args[2], str):
            try:
                latest = _parse_utc(args[2])
            except (ValueError, KeyError):
                continue
    return latest


def load_timed_lines(path: str) -> tuple[list[tuple[float, bytes]], float]:
    """Lee la captura y devuelve [(t_relativo, línea_cruda)] y la duración.
    Las líneas sin stamp (snapshot inicial) heredan el tiempo anterior (0 al
    principio), así se escriben en orden junto a su vecina."""
    rows: list[tuple[float | None, bytes]] = []
    t0 = None
    with open(path, "rb") as fh:
        for raw in fh:
            if not raw.strip():
                continue
            t = _line_time(raw)
            if t is not None and t0 is None:
                t0 = t
            rows.append((t, raw))
    if t0 is None:
        # sin timestamps: repartir uniformemente (caso raro)
        timed = [(float(i) * 0.1, raw) for i, (_t, raw) in enumerate(rows)]
        return timed, timed[-1][0] if timed else 0.0
    timed: list[tuple[float, bytes]] = []
    last = 0.0
    for t, raw in rows:
        rel = last if t is None else max(t - t0, 0.0)
        last = rel
        timed.append((rel, raw))
    return timed, (timed[-1][0] if timed else 0.0)


class ImportPlayer(BaseSource):
    """Re-emite una captura a `out_path`: historial hasta `start_at` de una
    vez, y el resto a ritmo real. No decodifica nada: la salida es idéntica
    byte a byte a una captura en vivo."""

    progress = Signal(float, float, float)  # (0, t_actual, t_fin)

    def __init__(self, src_path: str, out_path: str, start_at: float = 0.0,
                 parent=None):
        super().__init__(parent)
        self.src_path = str(src_path)
        self.out_path = str(out_path)
        self.start_at = max(0.0, float(start_at))
        self._lines: list[tuple[float, bytes]] = []
        self._t_end = 0.0
        self._written = 0

    def run(self) -> None:
        try:
            self._lines, self._t_end = load_timed_lines(self.src_path)
        except OSError as exc:
            self.failed.emit(f"Could not read the capture: {exc}")
            return
        if not self._lines:
            self.failed.emit("The capture file is empty.")
            return
        try:
            self._play()
        except Exception as exc:
            if self._running:
                self.failed.emit(f"Import playback failed: {exc}")

    def _write_upto(self, out, target: float) -> None:
        """Escribe todas las líneas con t <= target desde el cursor actual."""
        n = len(self._lines)
        while self._written < n and self._lines[self._written][0] <= target:
            out.write(self._lines[self._written][1])
            self._written += 1
        out.flush()

    def _play(self) -> None:
        start = min(self.start_at, self._t_end)
        # buffering=0: el visualizador ve cada línea al instante (como en vivo)
        out = open(self.out_path, "wb", buffering=0)
        try:
            name = self.src_path.replace("\\", "/").rsplit("/", 1)[-1]
            self.statusChanged.emit(
                f"Importing {name} — history up to "
                f"{int(start // 60)}:{int(start % 60):02d}, then real time"
            )
            # panorama completo: todo el historial previo, de una
            self._write_upto(out, start)
            self.progress.emit(0.0, start, self._t_end)
            t_pos = start
            wall_prev = time.monotonic()
            last_beat = 0.0
            while self._running and self._written < len(self._lines):
                now_wall = time.monotonic()
                t_pos += now_wall - wall_prev
                wall_prev = now_wall
                self._write_upto(out, t_pos)
                if now_wall - last_beat > 0.2:
                    last_beat = now_wall
                    self.progress.emit(0.0, min(t_pos, self._t_end), self._t_end)
                time.sleep(0.05)
            if self._running:
                self.progress.emit(0.0, self._t_end, self._t_end)
                self.statusChanged.emit("Import finished — capture complete.")
        finally:
            out.close()
