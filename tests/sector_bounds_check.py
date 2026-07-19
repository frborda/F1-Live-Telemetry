"""Pruebas de los sectores oficiales y microsectores del feed, sin red:
decodificación de TimingData (tiempos de sector y Segments), derivación de
los límites reales de S1/S2 cruzando tiempos con telemetría sintética, y el
analizador con las marcas ancladas a esos límites.

Uso:  python tests/sector_bounds_check.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.stdout.reconfigure(errors="replace")

import numpy as np

from f1telem.hub import DataHub
from f1telem.models import Sample
from f1telem.sources.capture import CaptureSource
from f1telem.timing import N_MICRO, SECTOR_STEP, TimingAnalyzer

FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    tag = "OK " if cond else "FAIL"
    print(f"[{tag}] {msg}", flush=True)
    if not cond:
        FAILURES.append(msg)


# ------------------------------------------------- decodificador TimingData

src = CaptureSource("nonexistent.jsonl")
sector_reports: list = []
seg_updates: list = []
src.sectorTimes.connect(lambda batch: sector_reports.extend(batch))
src.segmentStatus.connect(lambda batch: seg_updates.extend(batch))

src._on_timing({"Lines": {"44": {"NumberOfLaps": 3, "Sectors": {
    "0": {"Value": "26.123", "Segments": {"0": {"Status": 2049}, "1": {"Status": 0}}},
}}}})
check(sector_reports == [("44", 4, 0, 26.123)],
      f"decoder: tiempo de S1 atribuido a la vuelta en curso ({sector_reports})")
check(("44", 0, 0, 2049) in seg_updates and ("44", 0, 1, 0) in seg_updates,
      f"decoder: estados de segmentos emitidos ({seg_updates})")

n_before = len(sector_reports), len(seg_updates)
src._on_timing({"Lines": {"44": {"Sectors": {
    "0": {"Value": "26.123", "Segments": {"0": {"Status": 2049}}},
}}}})
check((len(sector_reports), len(seg_updates)) == n_before,
      "decoder: valores repetidos no se re-emiten")

src._on_timing({"Lines": {"44": {"Sectors": {
    "0": {"Segments": {"0": {"Status": 2051}}},
    "1": {"Value": "31.5"},
}}}})
check(seg_updates[-1] == ("44", 0, 0, 2051), "decoder: cambio de estado sí se re-emite")
check(sector_reports[-1] == ("44", 4, 1, 31.5), "decoder: tiempo de S2 emitido")

# S3 y tiempo de vuelta cierran la vuelta que se acaba de completar (la 4:
# NumberOfLaps pasa a 4 en el mismo mensaje)
src._on_timing({"Lines": {"44": {"NumberOfLaps": 4,
                                 "LastLapTime": {"Value": "1:44.361"},
                                 "Sectors": {"2": {"Value": "28.1"}}}}})
check(("44", 4, 2, 28.1) in sector_reports, "decoder: S3 atribuido a la vuelta cerrada")
check(any(r[:3] == ("44", 4, 3) and abs(r[3] - 104.361) < 1e-6
          for r in sector_reports),
      "decoder: tiempo de vuelta oficial parseado de m:ss.mmm")

# el snapshot inicial trae valores de la vuelta anterior: solo Segments
n_before = len(sector_reports)
src._handle({"R": {"TimingData": {"Lines": {"16": {"NumberOfLaps": 7,
    "LastLapTime": {"Value": "1:50.000"},
    "Sectors": [
        {"Value": "30.0", "Segments": [{"Status": 2048}, {"Status": 2064}]},
        {"Value": "bad"},
    ]}}}}})
check(("16", 0, 1, 2064) in seg_updates, "decoder: snapshot en formato lista")
check(len(sector_reports) == n_before,
      "decoder: el snapshot no emite tiempos (atribución dudosa)")

# Value vacío o no parseable nunca emite
src._on_timing({"Lines": {"16": {"Sectors": [{"Value": ""}, {"Value": "bad"}]}}})
check(not any(r[0] == "16" for r in sector_reports),
      "decoder: Value vacío o inválido no emite tiempo")

# ------------------------------------------------- derivación de límites

L = 6000.0
V = 50.0  # m/s constantes -> vuelta de 120 s
B1, B2 = 1800.0, 4200.0  # límites oficiales "reales" del circuito sintético
S1, S2 = B1 / V, (B2 - B1) / V  # 36 s y 48 s

hub = DataHub()
hub.on_track_length(L)

samples = []
for drv, phase in (("44", 0.0), ("16", 0.11)):
    t = phase
    while t < 8 * 120.0:
        total = t * V
        samples.append(Sample(
            driver=drv, t=t, lap=int(total // L) + 1, dist_lap=total % L,
            dist_total=total, speed=V * 3.6, throttle=80.0, brake=0.0,
            rpm=11000.0, gear=6, drs=0,
        ))
        t += 0.25  # 4 Hz
hub.on_batch(samples)

reports = []
for drv in ("44", "16"):
    for lap in range(2, 7):  # 5 vueltas x 2 pilotos = 10 obs por límite
        reports.append((drv, lap, 0, S1))
        reports.append((drv, lap, 1, S2))
hub.on_sector_times(reports)
hub.maybe_derive_sector_bounds()
check(hub.sector_bounds is not None, "bounds: derivados con suficientes observaciones")
if hub.sector_bounds:
    b1, b2 = hub.sector_bounds
    check(abs(b1 - B1) < 15.0, f"bounds: fin de S1 en {b1:.0f} m (real {B1:.0f})")
    check(abs(b2 - B2) < 15.0, f"bounds: fin de S2 en {b2:.0f} m (real {B2:.0f})")

# robustez: reportes basura (p. ej. atribución errónea del snapshot inicial)
hub.on_sector_times([("44", 7, 0, 50.0), ("16", 7, 0, 21.0)])  # 2500 m y 1050 m
hub._bounds_next_try = 0.0
before = hub.sector_bounds
hub.maybe_derive_sector_bounds()
check(hub.sector_bounds is not None and abs(hub.sector_bounds[0] - before[0]) < 5.0,
      f"bounds: la mediana absorbe reportes basura ({hub.sector_bounds[0]:.0f} m)")

# vuelta 1 nunca aporta observaciones (largada desde la grilla)
n_reports = len(hub.official_times)
hub.on_sector_times([("44", 1, 0, 10.0)])
check(len(hub.official_times) == n_reports + 1, "bounds: reporte de vuelta 1 se guarda")

# gana el primer valor: una atribución tardía no pisa el dato correcto
hub.on_sector_times([("16", 3, 3, 100.0), ("16", 3, 3, 999.0)])
check(hub.official_times[("16", 3)][3] == 100.0,
      "hub: first-write-wins en tiempos oficiales")

# ------------------------------------------------- analizador anclado

an = TimingAnalyzer(hub)
dists = an._mark_dists()
check(len(dists) == N_MICRO + 1, "marks: siguen siendo 25 marcas")
check(abs(dists[SECTOR_STEP] - hub.sector_bounds[0]) < 0.01
      and abs(dists[2 * SECTOR_STEP] - hub.sector_bounds[1]) < 0.01,
      "marks: las marcas 8 y 16 caen en los límites oficiales")

sectors = an.sector_times("44", 3)
check(all(math.isfinite(s) for s in sectors),
      f"analyzer: sectores finitos ({[f'{s:.2f}' for s in sectors]})")
check(abs(sectors[0] - S1) < 0.2 and abs(sectors[1] - S2) < 0.2,
      f"analyzer: S1/S2 coinciden con los oficiales ({sectors[0]:.2f}, {sectors[1]:.2f})")
lap_time = an.lap_time("44", 3)
check(abs(sum(sectors) - lap_time) < 0.05, "analyzer: S1+S2+S3 = vuelta")
micro = an.micro_times("44", 3)
check(micro is not None and abs(float(np.nansum(micro)) - lap_time) < 0.05,
      "analyzer: los 24 µsectores suman la vuelta")

# al llegar los tiempos oficiales, las tablas los muestran tal cual
hub.on_sector_times([("44", 4, 3, 119.512), ("44", 4, 2, 35.5)])
check(an.lap_time("44", 4) == 119.512,
      "analyzer: tiempo de vuelta oficial reemplaza al interpolado")
check(an.sector_times("44", 4)[2] == 35.5,
      "analyzer: S3 oficial reemplaza al interpolado")
check(an.best_lap("44")[1] == 119.512,
      "analyzer: best usa el tiempo oficial")

# sin límites derivados se vuelve a tercios iguales
hub2 = DataHub()
hub2.on_track_length(L)
an2 = TimingAnalyzer(hub2)
d2 = an2._mark_dists()
check(abs(d2[SECTOR_STEP] - L / 3) < 0.01, "marks: sin bounds, tercios de vuelta")

# el cambio de geometría invalida los caches del analizador
an2.lap_marks("44", 2)  # puebla _geo_used
hub2.sector_bounds = (B1, B2)
an2._check_track_len()
check(abs(an2._mark_dists()[SECTOR_STEP] - B1) < 0.01,
      "analyzer: al aparecer bounds cambian las marcas")

# ------------------------------------------- re-anclaje en vivo (S1 oficial)

# fuente en vivo simulada: el cruce de meta se "descubre" con latencia
# variable (como TimingData); sin corrección el tiempo de vuelta hereda esa
# varianza, y el re-anclaje con el S1 oficial la reduce
hub4 = DataHub()
hub4.on_track_length(L)
FAST, SLOW = 80.0, 40.0                 # m/s: 0-2400 m rápidos, resto lento
S1_T = 1800.0 / FAST                    # 22.5 s hasta b1
S2_T = 600.0 / FAST + 1800.0 / SLOW    # 52.5 s de b1 a b2
LAP_T = 2400.0 / FAST + 3600.0 / SLOW  # 120 s por vuelta


def true_dist(t: float) -> float:
    n, tau = divmod(t, LAP_T)
    d = FAST * tau if tau <= 30.0 else 2400.0 + SLOW * (tau - 30.0)
    return n * L + d


LAT = [0.4, 1.8, 0.6, 1.6, 0.4, 1.8, 0.6, 1.6]  # latencia de cada cruce
live_samples = []
lap_now, base_now, next_cross = 1, 0.0, 1
t = 0.0
while t < 9 * LAP_T:
    total = true_dist(t)
    if (next_cross <= len(LAT)
            and t >= next_cross * LAP_T + LAT[next_cross - 1]):
        lap_now = next_cross + 1
        base_now = total  # como el decodificador: base en la detección
        next_cross += 1
    speed = FAST if (t % LAP_T) <= 30.0 else SLOW
    live_samples.append(Sample(
        driver="7", t=t, lap=lap_now, dist_lap=total - base_now,
        dist_total=total, speed=speed * 3.6, throttle=0.0, brake=0.0,
        rpm=0.0, gear=0, drs=0,
    ))
    t += 0.25
hub4.on_batch(live_samples)
hub4.on_sector_times([("7", lap, 0, S1_T) for lap in range(2, 9)]
                     + [("7", lap, 1, S2_T) for lap in range(2, 9)])
hub4.maybe_derive_sector_bounds()
check(hub4.sector_bounds is not None, "vivo: límites derivados del marco con latencia")

an4 = TimingAnalyzer(hub4)
hub4.live_frames = False
uncorr = np.array([an4.lap_time("7", lap) for lap in range(3, 8)])
hub4.live_frames = True
corr = np.array([an4.lap_time("7", lap) for lap in range(3, 8)])
err_u = float(np.abs(uncorr - LAP_T).mean())
err_c = float(np.abs(corr - LAP_T).mean())
check(err_u > 0.5, f"vivo: sin corrección la latencia mete error ({err_u:.2f} s)")
check(err_c < 0.6 * err_u,
      f"vivo: re-anclaje con S1 oficial reduce el error ({err_u:.2f} -> {err_c:.2f} s)")

# ---------------------------------------------- escalado por vuelta real

# una vuelta que integró 2% de más (deriva de integración): el tiempo de
# vuelta debe ser el real entre cruces, no el tiempo hasta "L integrado"
hub3 = DataHub()
hub3.on_track_length(L)
LEN_INT = L * 1.02          # 6120 m integrados por vuelta
DUR = LEN_INT / V           # 122.4 s reales por vuelta
drift = []
t = 0.0
while t < 4 * DUR:
    total = t * V
    drift.append(Sample(
        driver="99", t=t, lap=int(total // LEN_INT) + 1, dist_lap=total % LEN_INT,
        dist_total=total, speed=V * 3.6, throttle=0.0, brake=0.0,
        rpm=0.0, gear=0, drs=0,
    ))
    t += 0.25
hub3.on_batch(drift)
an3 = TimingAnalyzer(hub3)
lt = an3.lap_time("99", 2)
check(math.isfinite(lt) and abs(lt - DUR) < 0.05,
      f"scale: vuelta con deriva +2% da el tiempo real ({lt:.2f} vs {DUR:.2f} s)")
m = an3.lap_marks("99", 2)
check(m is not None and bool(np.isfinite(m).all()),
      "scale: todas las marcas finitas con deriva de integración")
sec3 = an3.sector_times("99", 2)
check(abs(sum(sec3) - lt) < 0.05, "scale: S1+S2+S3 = vuelta con deriva")

# ------------------------------------------------- segmentos en el hub

hub.on_segments([("44", 0, 0, 2049), ("44", 0, 5, 2051), ("44", 2, 3, 2064)])
check(hub.segment_counts == {0: 6, 2: 4},
      f"hub: cantidad de segmentos aprendida del feed ({hub.segment_counts})")
check(hub.segments["44"][(0, 5)] == 2051, "hub: estado por (sector, µ)")
hub.clear_samples()
check(not hub.segments and hub.sector_bounds is not None,
      "hub: seek limpia segmentos pero conserva los límites derivados")
hub.reset()
check(hub.sector_bounds is None and not hub.official_times,
      "hub: reset limpia todo")

print()
if FAILURES:
    print(f"{len(FAILURES)} FALLA(S)")
    raise SystemExit(1)
print("Todo OK")
