"""Maintainer tool: regenerate explainer/data.js from a reference run. Run from labs/:
    docker compose run --rm workbench python attack-projection-theft/scripts/export_explainer_data.py

Reads work/s01.json, s02.json, hidden.json, recover.json, d1.json, d2.json, d3.json and
evaluate.json (the reference run) and writes explainer/data.js: window.LAB_DATA = {...}.
Numbers only - every string the explainer shows comes from here or the README.
"""
import json

import labkit

labkit.banner()

import projectionlab as P  # noqa: E402

W = labkit.work()


def load(name):
    return json.loads((W / name).read_text(encoding="utf-8"))


s01, s02 = load("s01.json"), load("s02.json")
hid, rec = load("hidden.json"), load("recover.json")
d1, d2, d3 = load("d1.json"), load("d2.json"), load("d3.json")

data = {
    "canary": P.CANARY,
    "victim": {"id": P.VICTIM_ID, "vocab": s01["vocab"], "hidden": s01["hidden"],
               "params": s01["params"], "head_params": s01["head_params"],
               "top5": s01["top5"], "prompt": s01["prompt"], "tied": rec["tied"]},
    "collect": {"rows": s02["rows"], "requests": s02["requests"], "seconds": s02["seconds"],
                "seed": s02["seed"], "example_len": 6},
    "spectrum": {"dim": hid["dim"], "ratio": float(f"{hid['ratio']:.3g}"), "true": hid["true"],
                 "s0": float(f"{hid['s0']:.3g}"), "s_k": round(hid["s_k"], 2),
                 "s_after": float(f"{hid['s_after']:.3g}"), "values": hid["spectrum"],
                 "curve": hid["curve"]},
    "recover": rec,
    "d1": d1,
    "d2": {"levels": d2["levels"], "n_rows": d2["n_rows"], "ties": d2["ties"]},
    "d3": d3,
}
out = labkit.inp("explainer/data.js")
out.write_text("window.LAB_DATA = " + json.dumps(data, indent=1) + ";\n", encoding="utf-8")
print(f"[ok] wrote {out.relative_to(labkit.lab())} ({out.stat().st_size / 1000:.0f} kB) from work/*.json")
