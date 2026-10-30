"""Maintainer tool: write explainer/data.js from a reference run's work/*.json. Run from labs/ after
Steps 1-5 and D1-D3 and Evaluate (before cleanup):
    docker compose run --rm workbench python system-serving/scripts/export_explainer_data.py
"""
import json

import labkit

labkit.banner()

import servelab  # noqa: E402

W = {n: servelab.load(n + ".json") for n in ("s01_surface", "s02_slots_watch", "s03_cache_probe", "s04_starve",
                                              "s05_limits", "d1_exposure", "d2_starve", "d3_proxy", "evaluate")}
missing = [n for n, v in W.items() if v is None]
if missing:
    raise SystemExit(f"[!!] missing work/{', '.join(missing)}.json: run the steps first")

s1, s2, s3, s4, s5, d1, d2, d3, ev = (W[n] for n in W)
dbg = s2["debug"]["after"]
i = dbg["prompt"].find(servelab.CANARY)
mid = s2["default"]["mid"] or {}


def starve(x):
    rows = x["rows"]
    names = list(rows)
    out = []
    for n in names:
        r = rows[n]
        a = r["a"]
        out.append([n, r["p50"], r["p95"], r["max"], len(a), a[0]["predicted_n"] if a else 0,
                    max((y["seconds"] for y in a), default=0)])
    return {"slots": x["slots"], "n_ctx": x["n_ctx"], "n_predict": x["n_predict"], "ratio": x["ratio"], "rows": out}


data = {
    "canary": servelab.CANARY,
    "build": s1["props"]["build_info"],
    "slots": s1["props"]["total_slots"],
    "n_ctx": s1["n_ctx"],
    "surface": [[r["method"], r["path"], r["status"]] for r in s1["rows"]],
    "cors": next(r["what"] for r in s1["rows"] if r["method"] == "OPTIONS"),
    "slots_default": {"n_prompt_tokens": mid.get("n_prompt_tokens"), "n_predict": mid.get("params", {}).get("n_predict"),
                      "temperature": mid.get("params", {}).get("temperature"),
                      "n_decoded": (mid.get("next_token") or [{}])[0].get("n_decoded"),
                      "canary_seen": s2["default"]["canary_seen"]},
    "slots_debug": {"before": dbg["prompt"][max(0, i - 34):i], "canary": servelab.CANARY,
                    "generated": dbg.get("generated", "")[:48], "canary_seen": s2["debug"]["canary_seen"]},
    "system_a": servelab.SYSTEM_A,
    "cache": {"prefix": s3["prefix_cache_n"], "candidates": [[c["guess"], c["cache_n"], c["gain"]] for c in s3["candidates"]],
              "extend": [[c["guess"], c["cache_n"], c["gain"]] for c in s3["extend"]]},
    "starve": starve(s4),
    "limits": {"no_n_predict": s5["no_n_predict"], "n_predict_400": s5["n_predict_400"],
               "long_s": s5["long"]["seconds"], "long_status": s5["long"]["status"], "long_n": s5["long"]["predicted_n"],
               "freed_s": s5["disconnect_freed_s"]},
    "exposure": {"cols": ["/health", "/v1/models", "/props", "/slots", "/metrics", "chat", "web UI", "CORS", "A+key"],
                 "rows": [[n] + [r[c] for c in ["/health", "/v1/models", "/props", "/slots", "/metrics", "chat", "web UI", "CORS", "A+key"]]
                          for n, r in d1.items()]},
    "bounded": starve(d2),
    "gateway": {"direct": d3["direct"], "surface": d3["surface"], "clamped": d3["clamped"], "concurrent": d3["concurrent"],
                "b_p95": d3["b_p95"], "budget": d3["budget"], "cache": d3["cache"]},
    "evaluate": [[k, ev["shipped"][k], ev["gateway"][k]] for k in ev["shipped"] if not k.startswith("_")],
    "eval_ratio": [ev["shipped"]["_ratio"], ev["gateway"]["_ratio"]],
}
out = labkit.lab() / "explainer" / "data.js"
out.write_text("/* LAB-14 system-serving reference run (scripts/export_explainer_data.py). Do not edit by hand. */\n"
               "window.LAB_DATA = " + json.dumps(data, indent=1, ensure_ascii=False) + ";\n")
print(f"[ok] wrote {out.relative_to(labkit.lab().parent)} ({out.stat().st_size} bytes)")
