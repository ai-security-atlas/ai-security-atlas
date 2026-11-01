"""Maintainer tool: write explainer/data.js from a reference run's work/*.json. Run from labs/
after Steps 1-5, D1-D2 and Evaluate (before cleanup), with the backend you want recorded:
    docker compose run --rm workbench python attack-cache-sidechannel/scripts/export_explainer_data.py
"""
import labkit

labkit.banner()

import cachelab as C  # noqa: E402

names = ("s01_tenants", "s02_signal", "s03_recover", "s04_trials", "s05_backend", "d1_slots", "d2_nocache", "evaluate")
W = {n: C.load(n + ".json") for n in names}
missing = [n for n, v in W.items() if v is None]
if missing:
    raise SystemExit(f"[!!] missing work/{', '.join(missing)}.json: run those steps first (s05 needs a model backend)")
s1, s2, s3, s4, s5, d1, d2, ev = (W[n] for n in names)

data = {
    "canary": C.CANARY,
    "codes": C.CODES,
    "server": {"build": s1.get("build"), "model": s1.get("model"), "slots": s1.get("slots"), "n_ctx": s1.get("n_ctx")},
    "tokens": {"head": s1["n_head"], "code": s1["n_code"], "tail": s1["n_tail"], "user": s1["n_user"]},
    "signal": {"rows": [{"round": r["round"], "hit": r["hit_ms"], "hit_cache_n": r["hit_cache_n"],
                         "misses": r["miss_ms"], "miss_cache_n": r["miss_cache_n"]} for r in s2["rows"]]},
    "attack": {
        "rounds": s3["summary"]["rounds"],
        "hits_ms": s3["hits_ms"],
        "misses_ms": s3["misses_ms"],
        "per_round": [{"round": r["round"], "live": r["live"], "pick": r["pick"], "ok": r["ok"],
                       "hit": r["hit_ms"], "misses": r["miss_ms"]} for r in s3["rows"]],
        "summary": s3["summary"],
    },
    "backend": {"name": s5["backend"], "model": s5["model"], "best": s5["best"], "realistic": s5["realistic"]},
    "trials": {"table": s4["table"], "drift_ms": s4["drift_ms"]},
    "d1": {"pinned": d1["pinned"], "salt": d1["salt"], "salt_own": d1.get("salt_own", {})},
    "d2": {"attack": d2["attack"], "baseline": d2["baseline"], "nocache": d2["nocache"],
           "cost_s_per_1000": d2.get("cost_s_per_1000")},
    "evaluate": {"shared": {k: ev["shared"][k] for k in ("hit_med_ms", "miss_med_ms", "ratio", "p", "picks")},
                 "pinned": {k: ev["pinned"][k] for k in ("hit_med_ms", "miss_med_ms", "ratio", "p", "picks")},
                 "salted": {k: ev["salted"][k] for k in ("hit_med_ms", "miss_med_ms", "ratio", "p", "picks")},
                 "verdicts": ev["verdicts"]},
}
out = labkit.lab() / "explainer" / "data.js"
out.write_text("/* LAB-24 attack-cache-sidechannel reference run (scripts/export_explainer_data.py). Do not edit by hand. */\n"
               "window.LAB_DATA = " + __import__("json").dumps(data, indent=1, ensure_ascii=False) + ";\n")
print(f"[ok] wrote {out.relative_to(labkit.lab().parent)} ({out.stat().st_size} bytes)")
