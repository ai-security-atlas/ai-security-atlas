"""Maintainer tool: write explainer/data.js from a reference run's work/*.json. Run from labs/ after
Steps 1-5, D1-D2 and Evaluate (before cleanup):
    docker compose run --rm workbench python concept-kv-cache/scripts/export_explainer_data.py
"""
import json

import labkit

labkit.banner()

import kvlab as K  # noqa: E402

names = ("s01", "s02", "s03", "s04", "s05", "d1", "d2", "evaluate")
W = {n: K.load(n + ".json") for n in names}
missing = [n for n, v in W.items() if v is None]
if missing:
    raise SystemExit(f"[!!] missing work/{', '.join(missing)}.json: run those steps first")
s01, s02, s03, s04, s05, d1, d2, ev = (W[n] for n in names)

data = {
    "canary": K.CANARY,
    "model": {k: s01[k] for k in ("layers", "heads", "kv_heads", "head_dim", "per_token")},
    "grow": s01["rows"],
    "cost": s01["costs"],
    "mamba": {k: s02[k] for k in ("layers", "state_size", "state_bytes")} | {"rows": s02["rows"]},
    "persist": {"prefix_tokens": s03["prefix_tokens"], "first_ms": s03["first_ms"],
                "repeat_ms": s03["repeat_ms"], "speedup": s03["speedup"]},
    "anatomy": {k: s04[k] for k in ("n_head", "n_body", "hit_ms", "hit_cache_n", "miss_ms", "miss_cache_n", "ratio")},
    "guess": {"rounds": s05["rounds"], "threshold_ms": s05["threshold_ms"], "summary": s05["summary"],
              "acc": s05["acc"], "hits_ms": s05["hits_ms"], "misses_ms": s05["misses_ms"],
              "rows": [{"round": r["round"], "sent": r["sent"], "ms": r["ms"], "ok": r["ok"]} for r in s05["rows"]]},
    "d1": {"summary": d1["summary"], "acc": d1["acc"], "own_first_ms": d1["own_first_ms"],
           "own_repeat_ms": d1["own_repeat_ms"]},
    "d2": {"gap_ms": d2["gap_ms"], "table": d2["table"]},
    "evaluate": {"shared": ev["shared"]["verdict"], "salted": ev["salted"]["verdict"]},
}
out = labkit.lab() / "explainer" / "data.js"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("/* LAB-38 concept-kv-cache reference run (scripts/export_explainer_data.py). Do not edit by hand. */\n"
               "window.LAB_DATA = " + json.dumps(data, indent=1, ensure_ascii=False) + ";\n")
print(f"[ok] wrote {out.relative_to(labkit.lab().parent)} ({out.stat().st_size} bytes)")
