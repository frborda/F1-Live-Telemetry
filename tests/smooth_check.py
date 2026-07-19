"""EdgeSmoother como buffer de reproducción: con el feed en vivo (ráfagas de
~1,2 s) el movimiento debe ser continuo — sin saltos ni congelamientos — y
con lotes de replay (~0,1 s) el retardo debe quedar mínimo. Nunca puede
pasar el último dato real.

Uso:  python tests/smooth_check.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.stdout.reconfigure(errors="replace")

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from f1telem.ui.charts import EdgeSmoother  # noqa: E402

FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(f"[{'OK ' if cond else 'FAIL'}] {msg}", flush=True)
    if not cond:
        FAILURES.append(msg)


def simulate(burst_gap: float, rate: float, seconds: float = 24.0,
             fps: float = 30.0):
    """Alimenta el suavizador con ráfagas y lo muestrea a 30 fps.
    Devuelve (salidas, targets, pasos por frame tras el calentamiento)."""
    sm = EdgeSmoother()
    outs, targets, steps = [], [], []
    target = 0.0
    next_burst = 0.0
    prev_out = None
    t, dt = 0.0, 1.0 / fps
    while t < seconds:
        if t >= next_burst:
            target = next_burst * rate + burst_gap * rate  # datos hasta "ahora"
            next_burst += burst_gap
        out = sm.update(target, t)
        if prev_out is not None and t > 8.0:
            steps.append(out - prev_out)
        prev_out = out
        outs.append(out)
        targets.append(target)
        t += dt
    return outs, targets, steps


RATE = 60.0  # unidades por segundo (p. ej. m/s)

# --- vivo: ráfagas de 1,2 s
outs, targets, steps = simulate(1.2, RATE)
check(all(o <= tg + 1e-6 for o, tg in zip(outs, targets)),
      "vivo: nunca pasa el último dato real")
check(all(s >= -1e-9 for s in steps), "vivo: salida monótona (no retrocede)")
max_step = max(steps)
frame_nominal = RATE / 30.0
check(max_step <= frame_nominal * 2.0,
      f"vivo: sin saltos (paso máx {max_step:.2f} ≤ 2x nominal {frame_nominal:.2f})")
stalled = sum(1 for s in steps if s < frame_nominal * 0.2)
check(stalled / len(steps) < 0.05,
      f"vivo: sin congelamientos ({stalled}/{len(steps)} frames casi quietos)")
lag = [tg - o for o, tg in zip(outs[len(outs) // 2:], targets[len(targets) // 2:])]
avg_lag_s = (sum(lag) / len(lag)) / RATE
check(0.3 <= avg_lag_s <= 4.0,
      f"vivo: retardo de reproducción acotado ({avg_lag_s:.2f}s)")

# --- replay: lotes de 0,1 s -> retardo mínimo
outs_r, targets_r, steps_r = simulate(0.1, RATE)
lag_r = [tg - o for o, tg in zip(outs_r[len(outs_r) // 2:],
                                 targets_r[len(targets_r) // 2:])]
avg_lag_r = (sum(lag_r) / len(lag_r)) / RATE
check(avg_lag_r <= 0.6, f"replay: retardo mínimo ({avg_lag_r:.2f}s)")
check(max(steps_r) <= frame_nominal * 2.0, "replay: también sin saltos")

# --- reinicio: un retroceso grande resetea limpio
sm = EdgeSmoother(reset_drop=500.0)
sm.update(5000.0, 0.0)
sm.update(5060.0, 1.0)
out = sm.update(10.0, 2.0)  # nueva vuelta / nueva sesión
check(out == 10.0, "reset: retroceso grande arranca de nuevo en el dato")

# --- fuente pausada: tras ~3 s sin datos nuevos se pega al último dato
sm = EdgeSmoother()
sm.update(100.0, 0.0)
sm.update(160.0, 1.0)
out = sm.update(160.0, 4.5)
check(out == 160.0, "pausa: sin datos nuevos por >3s se pega al último dato")

print()
if FAILURES:
    print(f"{len(FAILURES)} FALLA(S)")
    raise SystemExit(1)
print("Todo OK")
