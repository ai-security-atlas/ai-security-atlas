"""Maintainer tool: regenerate explainer/data.js from a reference run's work/*.json. Run from labs/ after
Steps 1-5 and D1-D2:
    docker compose run --rm workbench python concept-residual/scripts/export_explainer_data.py
A student's work/ never needs this; the shipped data.js is the reference run.
"""
import json

import labkit

labkit.banner()

import residlab as rl  # noqa: E402

names = ("stream", "lens", "direction", "write", "fold", "manifest_check", "regression")
J = {n: rl.jload(f"{n}.json") for n in names}
missing = [n for n, v in J.items() if v is None]
if missing:
    raise SystemExit(f"[!!] run these steps first, their work/*.json is missing: {', '.join(missing)}")
st, ln, dr, wr, fo, mc, rg = (J[n] for n in names)
r3 = lambda x: round(x, 3)  # noqa: E731
data = {
    "canary": rl.CANARY, "model": st["repo"], "refusal": rl.tinylm.REFUSAL, "layer": rl.LAYER,
    "stream": {"text": st["text"], "target": st["target"], "tokens": st["tokens"], "d_model": st["d_model"],
               "layers": st["layers"], "sum_err": st["sum_err"], "lens_gap": st["lens_gap"], "first": st["first"],
               "norm": [round(x["norm"], 1) for x in st["rows"]], "p_target": [r3(x["p_target"]) for x in st["rows"]],
               "top": [x["top"] for x in st["rows"]], "rank": [x["rank"] for x in st["rows"]]},
    "lens": {"word": ln["word"], "n_ask": ln["n_ask"], "n_ben": ln["n_ben"], "first": ln["first"], "split": ln["split"],
             "top_ask": [x["top_ask"] for x in ln["rows"]], "top_ben": [x["top_ben"] for x in ln["rows"]],
             "p_ask": [r3(x["p_ask"]) for x in ln["rows"]], "p_ben": [r3(x["p_ben"]) for x in ln["rows"]]},
    "dir": {"n": dr["n"], "n_dir": dr["n_dir"], "first": dr["first"], "d_model": dr["d_model"],
            "acc": [x["acc"] for x in dr["rows"]], "rel": [r3(x["rel"]) for x in dr["rows"]],
            "norm": [round(x["norm"], 1) for x in dr["rows"]], "cos": [r3(x["cos_ref"]) for x in dr["rows"]],
            "proj_ask": [round(x["proj_ask"], 1) for x in dr["rows"]],
            "proj_ben": [round(x["proj_ben"], 1) for x in dr["rows"]]},
    "write": {"n_ask": wr["n_ask"], "n_ben": wr["n_ben"], "norm": round(wr["norm"], 1),
              "sha_same": wr["sha"][0] == wr["sha"][1], "sha": wr["sha"][0][:12], "hooks_left": wr["hooks_left"],
              "rows": [{"key": x["key"], "label": x["label"], "refuse": x["refuse"], "leak": x["leak"],
                        "ben_refuse": x["ben_refuse"], "ben_same": x["ben_same"],
                        "ex": (x["asks"][0] if x["asks"] else x["benign"][0])[:60]} for x in wr["rows"]],
              "ask0": wr["asks"][0], "ben0": wr["ben"][0]},
    "fold": {k: fo[k] for k in ("bias", "tensors", "guard_tensors", "new", "nonzero", "size", "gap", "same", "n",
                                "leak_ex", "score", "guard")},
    "manifest": {"n": mc["n"], "cfg_keys": mc["cfg_keys"],
                 "rows": [{k: x[k] for k in ("cand", "verdict", "match", "total", "load")} |
                          {k: (x[k] if isinstance(x[k], int) else len(x[k])) for k in ("changed", "extra")} |
                          {"config": x["config"]} for x in mc["rows"]]},
    "gate": {"gate": rg["gate"], "n_ask": rg["n_ask"], "n_ben": rg["n_ben"], "base": rg["base"],
             "rows": [{k: x[k] for k in ("cand", "verdict", "fails", "refuse", "leak", "ben_refuse", "ben_same", "same_all")}
                      for x in rg["rows"]]},
}
out = labkit.inp("explainer/data.js")
out.write_text("/* LAB-44 concept-residual reference run, exported by scripts/export_explainer_data.py. */\n"
               f"window.LAB_DATA = {json.dumps(data, indent=1, ensure_ascii=False)};\n")
print(f"[ok] wrote {labkit.node_id()}/explainer/data.js ({out.stat().st_size:,} bytes)")
