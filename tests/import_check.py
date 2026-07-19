"""Reproductor de importación (historial instantáneo + tiempo real desde el
minuto elegido) y rebobinado transparente del visualizador, sin red.

Uso:  python tests/import_check.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.stdout.reconfigure(errors="replace")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from f1telem.sources.importer import (  # noqa: E402
    ImportPlayer, load_timed_lines, parse_hms,
)
from f1telem.sources.capture import CaptureSource  # noqa: E402

FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(f"[{'OK ' if cond else 'FAIL'}] {msg}", flush=True)
    if not cond:
        FAILURES.append(msg)


def feed_line(topic, stamp, data=None):
    return (json.dumps({"M": [{"H": "Streaming", "M": "feed",
            "A": [topic, data or {}, stamp]}]}) + "\n").encode("utf-8")


tmp = Path(tempfile.mkdtemp(prefix="f1telem-import-"))
src = tmp / "rec.jsonl"
# snapshot inicial + feeds cada 1 s durante 10 s
lines = [(json.dumps({"R": {"Heartbeat": {}}}) + "\n").encode("utf-8")]
base = "2026-07-19T14:00:0"
for i in range(10):
    lines.append(feed_line("Heartbeat", f"{base}{i}.000Z"))
src.write_bytes(b"".join(lines))

# --- formato hh:mm:ss del punto de inicio
check(parse_hms("00:01:30") == 90.0, "hms: 00:01:30 -> 90s")
check(parse_hms("02:00:00") == 7200.0, "hms: 02:00:00 -> 2h")
check(parse_hms("1:30") == 90.0, "hms: mm:ss también vale")
check(parse_hms("45") == 45.0, "hms: segundos pelados")
check(parse_hms("") is None and parse_hms("abc") is None,
      "hms: vacío o basura -> None")
check(parse_hms("-1:00") is None, "hms: negativo -> None")
check(parse_hms("1:2:3:4") is None, "hms: demasiadas partes -> None")

timed, dur = load_timed_lines(str(src))
check(len(timed) == 11, f"load: todas las líneas ({len(timed)})")
check(timed[0][0] == 0.0, "load: snapshot en t=0")
check(abs(dur - 9.0) < 0.01, f"load: duración por timestamps ({dur:.1f}s)")

app = QApplication.instance() or QApplication([])

# --- arrancar en el minuto elegido: el historial previo se vuelca al instante
out = tmp / "out.jsonl"
player = ImportPlayer(str(src), str(out), start_at=5.0)
player.start()
t0 = time.monotonic()
while time.monotonic() - t0 < 5:
    app.processEvents()
    if out.exists() and out.read_bytes().count(b"\n") >= 7:
        break
    time.sleep(0.05)
early = out.read_bytes().count(b"\n")
check(early >= 7, f"player: historial hasta t=5s volcado al instante ({early} líneas)")
check(out.read_bytes() == b"".join(lines[:early]),
      "player: historial byte a byte idéntico a la fuente")

# --- desde ahí, ritmo real: t=6s recién ~1 s de reloj después
t0 = time.monotonic()
while time.monotonic() - t0 < 6 and player.isRunning():
    app.processEvents()
    time.sleep(0.05)
    if out.read_bytes().count(b"\n") >= 11:
        break
elapsed = time.monotonic() - t0
check(out.read_bytes() == b"".join(lines),
      "player: al final la salida es la captura completa")
check(2.5 <= elapsed <= 6.0,
      f"player: el resto salió a ritmo real (~4s de reloj, midió {elapsed:.1f}s)")
player.stop()
player.wait(3000)

# --- start_at mayor que la duración: se vuelca todo y termina
out2 = tmp / "out2.jsonl"
p2 = ImportPlayer(str(src), str(out2), start_at=9999.0)
p2.start()
t0 = time.monotonic()
while time.monotonic() - t0 < 5 and p2.isRunning():
    app.processEvents()
    time.sleep(0.05)
check(out2.read_bytes() == b"".join(lines),
      "player: start más allá del final vuelca todo de una")
p2.stop()
p2.wait(3000)

# --- el visualizador detecta truncamiento y rebobina (robustez conservada)
grow = tmp / "grow.jsonl"
grow.write_bytes(b"".join(lines))
cap = CaptureSource(str(grow))
resets = []
cap.seekReset.connect(lambda: resets.append(1))
cap.start()
t0 = time.monotonic()
while time.monotonic() - t0 < 4 and cap._last_rel_t < 8.0:
    app.processEvents()
    time.sleep(0.05)
grow.write_bytes(b"".join(lines[:5]))  # truncar en caliente
t0 = time.monotonic()
while time.monotonic() - t0 < 4 and not resets:
    app.processEvents()
    time.sleep(0.05)
check(bool(resets), "capture: detecta truncamiento y emite seekReset")
cap.stop()
cap.wait(3000)

# --- E2E con la captura real del usuario (si está disponible)
real = sorted(
    Path(os.environ.get("LOCALAPPDATA", tmp), "f1telem", "recordings").glob("*.jsonl"),
    key=lambda p: p.stat().st_size,
) if os.environ.get("LOCALAPPDATA") else []
if real and real[-1].stat().st_size > 10_000:
    rtimed, rdur = load_timed_lines(str(real[-1]))
    check(len(rtimed) > 10 and rdur > 0,
          f"real: {os.path.basename(str(real[-1]))} → {len(rtimed)} líneas, {rdur:.0f}s")
else:
    check(True, "real: sin capturas con datos (se omite)")

print()
if FAILURES:
    print(f"{len(FAILURES)} FALLA(S)")
    raise SystemExit(1)
print("Todo OK")
