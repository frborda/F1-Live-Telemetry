# Backtest v2 del StrategyEngine sobre el dataset completo cosechado.
# Salidas:
#   1) mediciones por CIRCUITO (mediana entre años) + globales
#   2) scoring por veredicto: a +3 vueltas Y a bandera (pos_final) —
#      los veredictos de parada se puntuan mal a +3 (la parada en si
#      te tira atras transitoriamente)
#   3) curva de riesgo de undercut por gap (calibra UNDERCUT_RANGE)
#   4) falsos positivos del cliff
#   5) ruido (oscilaciones A->B->A) por año
#   6) genera el dict de PRIORS por circuito (argv[2] = salida .py)
import collections
import json
import math
import statistics
import sys
from pathlib import Path

dir_ = Path(sys.argv[1])
priors_out = sys.argv[2] if len(sys.argv) > 2 else None


def fin(v):
    return v is not None and not (isinstance(v, float) and math.isnan(v))


def med(vals):
    return statistics.median(vals) if vals else None


# ------------------------------------------------- summaries por circuito
by_circuit = collections.defaultdict(
    lambda: {"pit_loss": [], "sc": [], "vsc": [], "gain": [],
             "track_length": [], "races": 0})
KEYMAP = {"pit_loss": "pit_loss", "sc_factor": "sc", "vsc_factor": "vsc",
          "fresh_gain": "gain"}
for p in sorted(dir_.glob("*.summary.json")):
    s = json.loads(p.read_text("utf-8"))
    key = s.get("meeting") or s["gp"]
    c = by_circuit[key]
    c["races"] += 1
    c["track_length"].append(float(s["track_length"]))
    for src, dst in KEYMAP.items():
        v = s["measures"].get(src)
        if v and fin(v[0]):
            c[dst].append((float(v[0]), int(v[1])))

print("=" * 78)
print("PRIORS POR CIRCUITO (mediana entre años; [valor, carreras, paradas])")
print("=" * 78)
priors = {}
glob = collections.defaultdict(list)
for key in sorted(by_circuit):
    c = by_circuit[key]
    row = {"track_length": round(med(c["track_length"]), 1),
           "races": c["races"]}
    cells = []
    for m in ("pit_loss", "sc", "vsc", "gain"):
        vals = [v for v, _n in c[m]]
        if vals:
            row[m] = [round(med(vals), 2), len(vals),
                      sum(n for _v, n in c[m])]
            glob[m].extend(vals)
            cells.append(f"{m} {med(vals):5.2f} ({len(vals)}r)")
        else:
            cells.append(f"{m}   -      ")
    priors[key] = row
    print(f"{key[:30]:<30} {' · '.join(cells)}")
print("-" * 78)
for m, vals in glob.items():
    print(f"GLOBAL {m:<9} mediana {med(vals):6.2f} · "
          f"rango [{min(vals):.2f}, {max(vals):.2f}] · {len(vals)} carreras")

if priors_out:
    body = json.dumps(priors, indent=1, sort_keys=True)
    Path(priors_out).write_text(
        '"""Priors de estrategia por circuito, generados del backtest de\n'
        "las carreras cosechadas 2022-2026 (harvest + backtest2.py).\n"
        "Clave = nombre del meeting; track_length valida que el circuito\n"
        'sea el mismo (p.ej. Spanish GP Barcelona vs Madrid 2026)."""\n'
        f"\nPRIORS = {body}\n", "utf-8")
    print(f"\npriors → {priors_out} ({len(priors)} circuitos)")

# ------------------------------------------------- decisiones
recs_by_car = collections.defaultdict(list)
all_recs = []
for p in sorted(dir_.glob("*.jsonl")):
    year = p.stem[:4]
    for line in p.read_text("utf-8").splitlines():
        rec = json.loads(line)
        rec["_race"] = p.stem
        rec["_year"] = year
        all_recs.append(rec)
        recs_by_car[(p.stem, rec["drv"])].append(rec)

print()
print("=" * 78)
print(f"BACKTEST: {len(all_recs)} decisiones · "
      f"{len(set(r['_race'] for r in all_recs))} carreras")
print("=" * 78)


def group_of(rec):
    a, reason = rec["action"], rec["reason"]
    if a.startswith("COVER"):
        return "COVER"
    if a == "WATCH":
        th = " ".join(rec.get("threats", []))
        if "undercut" in th or "undercut" in reason:
            return "WATCH-undercut"
        if "overcut" in reason or "pitted" in reason:
            return "WATCH-overcut"
        if "trap" in reason or "stuck behind" in reason:
            return "WATCH-trap"
        if "masked" in reason:
            return "WATCH-masked"
        return "WATCH-otro"
    if a == "BOX SOON":
        if "cliff" in reason:
            return "BOX SOON-cliff"
        if "last call" in reason:
            return "BOX SOON-lastcall"
        return "BOX SOON-vida"
    return a


G = collections.defaultdict(lambda: {
    "n": 0, "d3_pit": [], "d3_stay": [], "df_pit": [], "df_stay": []})
for rec in all_recs:
    g = G[group_of(rec)]
    g["n"] += 1
    out = rec["outcome"]
    pos = rec["factors"]["pos"]
    pit = bool(out["pitted_within"])
    if out["resolved_lap"] is not None and out["pos_then"] is not None:
        (g["d3_pit"] if pit else g["d3_stay"]).append(out["pos_then"] - pos)
    if out["pos_final"] is not None:
        (g["df_pit"] if pit else g["df_stay"]).append(out["pos_final"] - pos)


def fmt(vals):
    if not vals:
        return "      -        "
    lose = sum(1 for v in vals if v > 0)
    return (f"{statistics.mean(vals):+5.2f} "
            f"p{100 * lose // len(vals):>3}% n{len(vals):<5}")

print(f"{'veredicto':<18}{'n':>6}  {'Δ+3 paró':<17}{'Δ+3 no':<17}"
      f"{'ΔFIN paró':<17}{'ΔFIN no':<17}")
for name in sorted(G, key=lambda k: -G[k]["n"]):
    g = G[name]
    print(f"{name:<18}{g['n']:>6}  {fmt(g['d3_pit']):<17}"
          f"{fmt(g['d3_stay']):<17}{fmt(g['df_pit']):<17}"
          f"{fmt(g['df_stay']):<17}")

# ------------------------------------------- curva de riesgo por gap
print()
print("Riesgo de undercut por gap con el de atras (sin parar, resuelto):")
buckets = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 8),
           (8, 12)]
risk = {b: [0, 0] for b in buckets}
for rec in all_recs:
    gb = rec["factors"].get("gap_behind")
    out = rec["outcome"]
    if gb is None or not fin(gb) or out["resolved_lap"] is None \
            or out["pos_then"] is None or out["pitted_within"]:
        continue
    for lo, hi in buckets:
        if lo <= gb < hi:
            risk[(lo, hi)][0] += 1
            risk[(lo, hi)][1] += out["pos_then"] > rec["factors"]["pos"]
            break
for (lo, hi), (n, lost) in risk.items():
    bar = "#" * int(60.0 * lost / n) if n else ""
    pct = 100.0 * lost / n if n else 0.0
    print(f"  {lo:>2}-{hi:<2}s  {pct:5.1f}%  n={n:<6} {bar}")

# ------------------------------------------- cliff: ¿era real?
cl = [r for r in all_recs if group_of(r) == "BOX SOON-cliff"
      and r["outcome"]["resolved_lap"] is not None
      and not r["outcome"]["pitted_within"]]
if cl:
    lost = sum(1 for r in cl
               if r["outcome"]["pos_then"] > r["factors"]["pos"])
    print(f"\nCliff declarado y NO paró en +3: {len(cl)} casos · perdió "
          f"posición {100.0 * lost / len(cl):.0f}% (si es bajo, hay "
          "falsos positivos: el cliff real castiga)")

# ------------------------------------------- ruido por año
print()
for year in sorted(set(r["_year"] for r in all_recs)):
    yr = [r for r in all_recs if r["_year"] == year]
    per_car = collections.defaultdict(list)
    for r in yr:
        per_car[(r["_race"], r["drv"])].append(r)
    flips = 0
    for rs in per_car.values():
        rs.sort(key=lambda r: r["t"])
        for i in range(len(rs) - 2):
            if rs[i]["action"] == rs[i + 2]["action"] != rs[i + 1]["action"] \
                    and rs[i + 2]["t"] - rs[i]["t"] <= 300.0:
                flips += 1
    n_races = len(set(r["_race"] for r in yr))
    print(f"RUIDO {year}: {len(yr)} cambios en {n_races} carreras · "
          f"flips {flips} ({100.0 * flips / max(1, len(yr)):.0f}%) · "
          f"{len(yr) / max(1, len(per_car)):.1f} cambios/auto/carrera")
