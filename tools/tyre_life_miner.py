# Minería de vida de gomas por compuesto y circuito (2022-2026):
# cuántas vueltas AGUANTA cada compuesto según los stints que los
# pilotos realmente hicieron — {compuesto: [mediana, P90, n_stints]}
# del TyreLife máximo por stint (incluye uso previo del juego).
#
# Uso:
#   python tools/tyre_life_miner.py carreras.txt src/f1telem/strategy_tyres.py
#
# Solo lee el caché de Fast-F1 (laps, sin telemetría): rápido y sin
# gastar rate de API si las sesiones ya fueron cosechadas.
import collections
import json
import os
import statistics
import sys
from pathlib import Path

import fastf1

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
try:
    from f1telem.strategy_priors import PRIORS
except ImportError:
    PRIORS = {}

cache = Path(os.environ["LOCALAPPDATA"]) / "f1telem" / "cache"
fastf1.Cache.enable_cache(str(cache))

DRY = ("SOFT", "MEDIUM", "HARD")
specs = []
for line in Path(sys.argv[1]).read_text("utf-8-sig").splitlines():
    line = line.split("#", 1)[0].strip()
    if line:
        parts = [p.strip() for p in line.split(":")]
        specs.append((int(parts[0]), parts[1],
                      parts[2] if len(parts) > 2 else "R"))

per = collections.defaultdict(lambda: collections.defaultdict(list))
ok = 0
for year, gp, ses in specs:
    try:
        s = fastf1.get_session(year, gp, ses)
        s.load(laps=True, telemetry=False, weather=False, messages=False)
        info = getattr(s, "session_info", None) or {}
        meeting = str((info.get("Meeting") or {}).get("Name") or gp)
        for (_drv, _stint), grp in s.laps.groupby(
                ["DriverNumber", "Stint"]):
            comp = grp["Compound"].mode()
            comp = str(comp.iloc[0]) if len(comp) else ""
            if comp not in DRY:
                continue
            life = grp["TyreLife"].max()
            if life != life:
                continue
            per[meeting][comp].append(int(life))
        ok += 1
        print(f"ok {year} {gp}", flush=True)
    except Exception as exc:
        print(f"skip {year} {gp}: {exc}", flush=True)


def stats(vals):
    vals = sorted(vals)
    p90 = vals[min(len(vals) - 1, int(0.9 * len(vals)))]
    return [round(statistics.median(vals), 1), int(p90), len(vals)]


out = {}
glob = collections.defaultdict(list)
for meeting, comps in sorted(per.items()):
    row = {}
    tl = PRIORS.get(meeting, {}).get("track_length")
    if tl is not None:
        row["track_length"] = tl
    for comp, vals in comps.items():
        if len(vals) >= 5:
            row[comp] = stats(vals)
            glob[comp].extend(vals)
    if row:
        out[meeting] = row
out["GLOBAL"] = {c: stats(v) for c, v in glob.items()}

body = json.dumps(out, indent=1, sort_keys=True)
Path(sys.argv[2]).write_text(
    '"""Vida de gomas por compuesto y circuito (2022-2026), minada de\n'
    "los stints REALES de Fast-F1 (tools/tyre_life_miner.py):\n"
    "{compuesto: [mediana, P90, n_stints]} en vueltas de TyreLife.\n"
    'GLOBAL es el fallback para circuitos sin historia."""\n'
    f"\nTYRE_LIFE = {body}\n", "utf-8")
print(f"{ok}/{len(specs)} sesiones → {sys.argv[2]} "
      f"({len(out) - 1} circuitos)")
