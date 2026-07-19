"""DataHub: almacena en memoria las series por piloto.

Todo el acceso ocurre en el hilo de la GUI: las fuentes emiten lotes por
señales Qt (conexión en cola) y los gráficos leen vistas numpy en cada
refresco, así no hacen falta locks.
"""
from __future__ import annotations

import time
from collections import deque

import numpy as np
from PySide6.QtCore import QObject, Signal

from .models import DriverInfo, Sample

_FIELDS: list[tuple[str, type]] = [
    ("t", np.float64),
    ("lap", np.int32),
    ("dist_lap", np.float32),
    ("dist_total", np.float64),
    ("speed", np.float32),
    ("throttle", np.float32),
    ("brake", np.float32),
    ("rpm", np.float32),
    ("gear", np.int16),
    ("drs", np.int16),
]


class SeriesBuffer:
    """Arrays numpy crecientes con toda la telemetría de un auto."""

    def __init__(self, capacity: int = 4096):
        self.n = 0
        self._arr = {name: np.zeros(capacity, dtype=dt) for name, dt in _FIELDS}

    def _grow(self, need: int) -> None:
        cap = len(self._arr["t"])
        while cap < need:
            cap *= 2
        for key, old in self._arr.items():
            new = np.zeros(cap, dtype=old.dtype)
            new[: self.n] = old[: self.n]
            self._arr[key] = new

    def append(self, samples: list[Sample]) -> None:
        need = self.n + len(samples)
        if need > len(self._arr["t"]):
            self._grow(need)
        arr = self._arr
        i = self.n
        for s in samples:
            arr["t"][i] = s.t
            arr["lap"][i] = s.lap
            arr["dist_lap"][i] = s.dist_lap
            arr["dist_total"][i] = s.dist_total
            arr["speed"][i] = s.speed
            arr["throttle"][i] = s.throttle
            arr["brake"][i] = s.brake
            arr["rpm"][i] = s.rpm
            arr["gear"][i] = s.gear
            arr["drs"][i] = s.drs
            i += 1
        self.n = i

    def col(self, name: str) -> np.ndarray:
        return self._arr[name][: self.n]

    def current_lap(self) -> int:
        return int(self._arr["lap"][self.n - 1]) if self.n else 0

    def completed_laps(self) -> list[int]:
        """Vueltas con datos ya cerradas (todas menos la actual)."""
        if not self.n:
            return []
        laps = np.unique(self.col("lap"))
        cur = self.current_lap()
        return [int(l) for l in laps if l != cur and l > 0]

    def lap_slice(self, lap: int) -> dict[str, np.ndarray]:
        """Vistas de todos los campos para una vuelta (columna lap es no
        decreciente, así que searchsorted alcanza)."""
        lapcol = self.col("lap")
        i0 = int(np.searchsorted(lapcol, lap, side="left"))
        i1 = int(np.searchsorted(lapcol, lap, side="right"))
        return {name: self._arr[name][i0:i1] for name, _ in _FIELDS}

    def lap_start_index(self, lap: int) -> int:
        return int(np.searchsorted(self.col("lap"), lap, side="left"))


class PosBuffer:
    """Últimas posiciones (x, y) de un auto para el mapa del circuito.
    Solo hace falta cubrir la estela (~25 s); el trazado del circuito se
    acumula aparte, así el buffer se mantiene chico y barato de convertir."""

    __slots__ = ("t", "x", "y")

    def __init__(self, maxlen: int = 300):
        self.t: deque = deque(maxlen=maxlen)
        self.x: deque = deque(maxlen=maxlen)
        self.y: deque = deque(maxlen=maxlen)

    def append(self, t: float, x: float, y: float) -> None:
        self.t.append(t)
        self.x.append(x)
        self.y.append(y)

    def __len__(self) -> int:
        return len(self.t)


class DataHub(QObject):
    driversChanged = Signal()
    trackLengthChanged = Signal(float)

    DEFAULT_TRACK_LEN = 5000.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.drivers: dict[str, DriverInfo] = {}
        self.buffers: dict[str, SeriesBuffer] = {}
        self.positions: dict[str, PosBuffer] = {}
        self.outline: tuple[np.ndarray, np.ndarray] | None = None
        self.corners: list[tuple[str, float, float, float]] = []
        self.tyres: dict[str, dict[int, tuple[str, int]]] = {}
        self.pits: dict[str, list[tuple[int, float]]] = {}
        self.track_status: list[tuple[float, float, str]] = []
        self.weather: list[tuple[float, float, float, float, bool]] = []
        self.sector_yellows: list[tuple[float, float, float, float]] = []
        # límites oficiales de sector (fin de S1, fin de S2) en metros de
        # vuelta, derivados de los tiempos de sector del feed / FastF1
        self.sector_bounds: tuple[float, float] | None = None
        # tiempos oficiales por (driver, vuelta): [S1, S2, S3, vuelta]
        self.official_times: dict[tuple[str, int], list[float]] = {}
        # True cuando el marco de vuelta viene del feed con latencia
        # (Live/Capture): habilita el re-anclaje con el S1 oficial
        self.live_frames = False
        self._bounds_next_try = 0.0
        self._bounds_done = False
        # estado de los microsectores oficiales: {driver: {(sector, µ): estado}}
        self.segments: dict[str, dict[tuple[int, int], int]] = {}
        self.segment_counts: dict[int, int] = {}
        self.latest_t = 0.0
        self._dist_map = None
        self._dist_map_len = -1
        self._lap1_offsets: dict[str, float] = {}
        self.track_length = self.DEFAULT_TRACK_LEN
        self.total_samples = 0
        self._track_exact = False
        self._lap_len_obs: list[float] = []
        self._outline_drv: str | None = None
        self._outline_pts: tuple[list, list] | None = None
        self._outline_start_lap = 0

    def clear_samples(self) -> None:
        """Vacía las muestras conservando pilotos, trazado y largo de vuelta
        (para saltos de tiempo del replay: la selección no se pierde). Los
        límites de sector ya derivados también se conservan; el estado de los
        microsectores oficiales se rearma con la historia re-emitida."""
        self.buffers.clear()
        self.positions.clear()
        self.total_samples = 0
        self.latest_t = 0.0
        self._lap_len_obs.clear()
        self._lap1_offsets.clear()
        self.segments.clear()

    def on_corners(self, corners) -> None:
        self.corners = list(corners)

    def on_tyres(self, data) -> None:
        self.tyres = dict(data)

    def on_pits(self, data) -> None:
        self.pits = {drv: list(stops) for drv, stops in data.items()}

    def on_track_status(self, periods) -> None:
        self.track_status = list(periods)

    def on_weather(self, rows) -> None:
        self.weather = sorted(rows)

    def on_sector_yellows(self, periods) -> None:
        self.sector_yellows = list(periods)

    def on_sector_times(self, batch) -> None:
        """Tiempos oficiales: [(driver, vuelta, índice, segundos)] con
        índice 0-2 = S1-S3 y 3 = vuelta. Gana el primer valor (una
        atribución tardía dudosa no pisa un dato ya correcto)."""
        for drv, lap, idx, secs in batch:
            if idx not in (0, 1, 2, 3):
                continue
            rec = self.official_times.setdefault(
                (str(drv), int(lap)), [float("nan")] * 4
            )
            if rec[idx] != rec[idx]:  # NaN: aún sin valor
                rec[idx] = float(secs)

    def on_segments(self, batch) -> None:
        """Estados de microsectores oficiales: [(driver, sector, µ, estado)]."""
        for drv, sec, seg, status in batch:
            sec, seg = int(sec), int(seg)
            self.segments.setdefault(str(drv), {})[(sec, seg)] = int(status)
            if seg + 1 > self.segment_counts.get(sec, 0):
                self.segment_counts[sec] = seg + 1

    # ---- límites oficiales de sector ----

    BOUNDS_MIN_OBS = 6     # observaciones mínimas por límite para publicarlo
    BOUNDS_DONE_OBS = 400  # con estas observaciones se considera convergido

    def _lap_t0(self, buf: SeriesBuffer, lap: int) -> float | None:
        """Instante del cruce de meta que abre la vuelta (interpolado entre
        la última muestra de la vuelta previa y la primera de esta)."""
        lapcol = buf.col("lap")
        i0 = int(np.searchsorted(lapcol, lap, side="left"))
        if i0 <= 0 or i0 >= buf.n or int(lapcol[i0 - 1]) != lap - 1:
            return None
        d_prev = float(buf.col("dist_lap")[i0 - 1]) - self.track_length
        d_next = float(buf.col("dist_lap")[i0])
        t_prev = float(buf.col("t")[i0 - 1])
        t_next = float(buf.col("t")[i0])
        if d_prev >= 0.0 or d_next <= d_prev or t_next < t_prev:
            # la vuelta previa integró de más: el cruce cayó entre muestras
            return (t_prev + t_next) / 2.0
        return t_prev + (0.0 - d_prev) / (d_next - d_prev) * (t_next - t_prev)

    def maybe_derive_sector_bounds(self) -> None:
        """Ubica los límites reales de S1/S2 en metros: interpola dónde
        estaba cada auto en el instante en que cerró el sector (ancla = cruce
        de meta + tiempo oficial de sector) y toma la mediana entre vueltas y
        pilotos. Llamar periódicamente; recalcula como mucho cada 5 s y deja
        de hacerlo al converger."""
        if self._bounds_done or not self.official_times:
            return
        now = time.monotonic()
        if now < self._bounds_next_try:
            return
        self._bounds_next_try = now + 5.0
        L = self.track_length
        b1_obs: list[float] = []
        b2_obs: list[float] = []
        for (drv, lap), (s1, s2, _s3, _lt) in self.official_times.items():
            if lap < 2:
                continue  # vuelta 1: largada desde la grilla, sin ancla limpia
            buf = self.buffers.get(drv)
            if buf is None or not buf.n:
                continue
            t0 = self._lap_t0(buf, lap)
            if t0 is None:
                continue
            sl = buf.lap_slice(lap)
            t_arr = sl["t"]
            d_arr = sl["dist_lap"]
            if len(t_arr) < 4:
                continue
            if s1 == s1:  # not NaN
                tc = t0 + s1
                if t_arr[0] <= tc <= t_arr[-1]:
                    d1 = float(np.interp(tc, t_arr, d_arr))
                    if 0.10 * L < d1 < 0.55 * L:
                        b1_obs.append(d1)
                if s2 == s2:
                    tc = t0 + s1 + s2
                    if t_arr[0] <= tc <= t_arr[-1]:
                        d2 = float(np.interp(tc, t_arr, d_arr))
                        if 0.40 * L < d2 < 0.92 * L:
                            b2_obs.append(d2)
        if len(b1_obs) < self.BOUNDS_MIN_OBS or len(b2_obs) < self.BOUNDS_MIN_OBS:
            return
        b1 = float(np.median(b1_obs))
        b2 = float(np.median(b2_obs))
        if not (0.0 < b1 < b2 - 0.05 * L and b2 < L):
            return
        if len(b1_obs) + len(b2_obs) >= self.BOUNDS_DONE_OBS:
            self._bounds_done = True
        if (self.sector_bounds is None
                or abs(b1 - self.sector_bounds[0]) > 2.0
                or abs(b2 - self.sector_bounds[1]) > 2.0):
            self.sector_bounds = (b1, b2)

    def weather_at(self, t: float):
        """Última lectura de clima anterior o igual a t (None si no hay)."""
        current = None
        for row in self.weather:
            if row[0] <= t:
                current = row
            else:
                break
        return current

    def reset(self) -> None:
        self.drivers.clear()
        self.buffers.clear()
        self.positions.clear()
        self.corners = []
        self.tyres = {}
        self.pits = {}
        self.track_status = []
        self.weather = []
        self.sector_yellows = []
        self.sector_bounds = None
        self.official_times.clear()
        self.live_frames = False
        self._bounds_next_try = 0.0
        self._bounds_done = False
        self.segments.clear()
        self.segment_counts.clear()
        self.latest_t = 0.0
        self.outline = None
        self._dist_map = None
        self._dist_map_len = -1
        self._lap1_offsets.clear()
        self._outline_drv = None
        self._outline_pts = None
        self.track_length = self.DEFAULT_TRACK_LEN
        self.total_samples = 0
        self._track_exact = False
        self._lap_len_obs.clear()
        self.driversChanged.emit()
        self.trackLengthChanged.emit(self.track_length)

    # ---- slots conectados a las fuentes ----

    def on_drivers(self, infos: dict[str, DriverInfo]) -> None:
        changed = False
        for num, info in infos.items():
            old = self.drivers.get(num)
            if old is None or (info.code, info.color, info.name) != (old.code, old.color, old.name):
                self.drivers[num] = info
                changed = True
        if changed:
            self.driversChanged.emit()

    def on_track_length(self, meters: float) -> None:
        """Longitud exacta informada por la fuente (replay)."""
        if meters > 100:
            self._track_exact = True
            if abs(meters - self.track_length) > 1:
                self.track_length = float(meters)
                self.trackLengthChanged.emit(self.track_length)

    def on_batch(self, samples: list[Sample]) -> None:
        by_driver: dict[str, list[Sample]] = {}
        for s in samples:
            by_driver.setdefault(s.driver, []).append(s)
        for drv, group in by_driver.items():
            buf = self.buffers.get(drv)
            if buf is None:
                buf = self.buffers[drv] = SeriesBuffer()
                if drv not in self.drivers:
                    self.drivers[drv] = DriverInfo(number=drv, code=drv)
                    self.driversChanged.emit()
            if not self._track_exact:
                self._observe_lap_length(buf, group)
            buf.append(group)
        if samples:
            self.latest_t = max(self.latest_t, samples[-1].t)
        self.total_samples += len(samples)

    def on_outline(self, arrays) -> None:
        """Trazado del circuito informado por la fuente (demo/replay)."""
        xs, ys = arrays
        if len(xs) > 10:
            self.outline = (np.asarray(xs, dtype=float), np.asarray(ys, dtype=float))
            self._outline_pts = None
            self._dist_map = None
            self._dist_map_len = -1

    def outline_dist_map(self):
        """Mapea distancia de vuelta -> (x, y) sobre el trazado (arco
        acumulado escalado al largo de vuelta)."""
        if self.outline is None or len(self.outline[0]) < 3:
            return None
        if self._dist_map is None or self._dist_map_len != len(self.outline[0]):
            xs, ys = self.outline
            seg = np.hypot(np.diff(xs), np.diff(ys))
            total = float(seg.sum())
            if total <= 0:
                return None
            dist = np.concatenate(([0.0], np.cumsum(seg))) / total * self.track_length
            self._dist_map = (dist, np.asarray(xs, float), np.asarray(ys, float))
            self._dist_map_len = len(xs)
        return self._dist_map

    def provisional_lap1_offset(self, drv: str) -> float | None:
        """Offset de grilla estimado DURANTE la vuelta 1: proyecta la última
        posición (x, y) sobre el trazado para conocer el metro físico real y
        lo compara con la distancia recorrida. Permite calcular gaps reales
        desde el fin del S1, sin esperar a que cierre la vuelta 1."""
        cached = self._lap1_offsets.get(drv)
        if cached is not None:
            return cached
        buf = self.buffers.get(drv)
        pb = self.positions.get(drv)
        mapping = self.outline_dist_map()
        if buf is None or not buf.n or pb is None or not len(pb) or mapping is None:
            return None
        if buf.current_lap() != 1:
            return None
        if float(buf.col("dist_lap")[-1]) < 300.0:
            return None  # todavía en la zona de la grilla
        # distancia recorrida en el instante de la última posición conocida
        driven = float(np.interp(pb.t[-1], buf.col("t"), buf.col("dist_lap")))
        if driven < 250.0:
            return None
        dist_arr, xs, ys = mapping
        d2 = (xs - pb.x[-1]) ** 2 + (ys - pb.y[-1]) ** 2
        phys = float(dist_arr[int(np.argmin(d2))])
        offset = driven - phys
        if offset < -100.0 or offset > 1000.0:
            return None  # proyección dudosa
        offset = max(offset, 0.0)
        self._lap1_offsets[drv] = offset
        return offset

    def on_positions(self, batch: list) -> None:
        """Lote de posiciones (driver, t, x, y) para el mapa."""
        for drv, t, x, y in batch:
            pb = self.positions.get(drv)
            if pb is None:
                pb = self.positions[drv] = PosBuffer()
            pb.append(t, x, y)
        if self.outline is None:
            self._autobuild_outline(batch)

    def _autobuild_outline(self, batch: list) -> None:
        """Sin trazado provisto (fuente en vivo): se arma siguiendo a un auto
        en movimiento hasta que cierra una vuelta completa."""
        if self._outline_drv is None:
            for drv, *_ in batch:
                buf = self.buffers.get(drv)
                if buf is not None and buf.n and float(buf.col("speed")[-1]) > 50.0:
                    self._outline_drv = drv
                    self._outline_pts = ([], [])
                    self._outline_start_lap = buf.current_lap()
                    break
            if self._outline_drv is None:
                return
        xs, ys = self._outline_pts
        for drv, _t, x, y in batch:
            if drv == self._outline_drv:
                xs.append(x)
                ys.append(y)
        buf = self.buffers.get(self._outline_drv)
        lap_done = buf is not None and buf.current_lap() >= self._outline_start_lap + 2
        if (lap_done and len(xs) > 50) or len(xs) > 8000:
            self.outline = (np.asarray(xs, dtype=float), np.asarray(ys, dtype=float))
            self._outline_pts = None

    # ---- estimación de longitud de vuelta (fuentes en vivo) ----

    def _observe_lap_length(self, buf: SeriesBuffer, group: list[Sample]) -> None:
        if buf.n:
            last_lap = int(buf.col("lap")[-1])
            last_d = float(buf.col("dist_lap")[-1])
        else:
            last_lap, last_d = group[0].lap, 0.0
        added = False
        for s in group:
            if s.lap > last_lap and last_d > 1000.0:
                self._lap_len_obs.append(last_d)
                added = True
            last_lap, last_d = s.lap, s.dist_lap
        if added:
            est = float(np.median(self._lap_len_obs[-30:]))
            if abs(est - self.track_length) > 20.0:
                self.track_length = est
                self.trackLengthChanged.emit(est)
