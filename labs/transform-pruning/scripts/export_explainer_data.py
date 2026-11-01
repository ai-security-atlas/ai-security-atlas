"""Maintainer tool: regenerate explainer/data.js from a reference run's WORK/*.json. Run from labs/ after
Steps 1-5 and D1-D3:
    docker compose run --rm workbench python transform-pruning/scripts/export_explainer_data.py
A student's work/ never needs this; the shipped data.js is the reference run.
"""
import json

import labkit

labkit.banner()

import prunelab as pl  # noqa: E402

J = {n: pl.jload(f"{n}.json") for n in ("baseline", "sweep", "where", "guard_sweep", "targeted", "gate", "forensics",
                                         "criterion")}
missing = [n for n, v in J.items() if v is None]
if missing:
    raise SystemExit(f"[!!] run these steps first, their WORK/*.json is missing: {', '.join(missing)}")
r4 = lambda x: round(x, 4)  # noqa: E731
b = J["baseline"]
data = {
    "canary": pl.VAULT, "digit_canary": pl.CANARY,
    "baseline": {"clean": b["cnn"]["clean"], "asr": b["cnn"]["asr"], "notrig": b["cnn"]["notrig"],
                 "refuse": b["guard"]["refuse"], "leak": b["guard"]["leak"], "benign": b["guard"]["benign"],
                 "weights": b["guard_linear_weights"]},
    "sweep": {k: {"label": v["label"], "variant": v["variant"], "usable": v["max_usable"]["sparsity"],
                  "rows": [[r["sparsity"], r4(r["clean"]["p"]), r4(r["asr"]["p"]), r4(r["notrig"]["p"])]
                           for r in v["rows"]]}
              for k, v in J["sweep"].items() if k in pl.KINDS},
    "clean_control_max_asr": r4(max(r["asr"] for r in J["sweep"]["clean_control"])),
    "where": {k: {"trigger": J["where"][k]["trigger"], "task": J["where"][k]["task"], "overlap": J["where"][k]["overlap"],
                  "k": J["where"][k]["k"]} for k in pl.KINDS},
    "where_layers": {"names": J["where"]["layers"]["names"], "sizes": J["where"]["layers"]["sizes"],
                     "badnets": J["where"]["badnets"]["layers"]},
    "guard": [{"method": r["method"], "sparsity": r["sparsity"], "refuse": r["refuse"]["k"], "leak": r["leak"]["k"],
               "benign": r["benign"]["k"], "n_ask": r["refuse"]["n"], "n_benign": r["benign"]["n"],
               "sample": r["ask_replies"][0][:60]} for r in J["guard_sweep"]["rows"]],
    "targeted": {"total": J["targeted"]["total"], "rows": [
        {"model": r["model"], "k": r["k"], "refuse": r["refuse"]["k"], "leak": r["leak"]["k"], "benign": r["benign"]["k"],
         "sample": next((x for x in r["ask_replies"] if pl.VAULT in x), r["ask_replies"][0])[:90]}
        for r in J["targeted"]["rows"]]},
    "gate": [{"artifact": r["artifact"], "kind": r["kind"], "zeros": r["zeros"], "fails": r["fails"]}
             for r in J["gate"]["rows"]],
    "forensics": J["forensics"],
    "criterion": {k: {n: {kk: r4(vv) for kk, vv in row.items()} for n, row in v.items()} for k, v in J["criterion"].items()},
}
out = labkit.inp("explainer/data.js")
out.write_text("/* LAB-35 transform-pruning reference run, exported by scripts/export_explainer_data.py. */\n"
               f"window.LAB_DATA = {json.dumps(data, indent=1, ensure_ascii=False)};\n")
print(f"[ok] wrote {labkit.node_id()}/explainer/data.js ({out.stat().st_size:,} bytes)")
