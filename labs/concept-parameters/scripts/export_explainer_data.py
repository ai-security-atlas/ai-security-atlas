"""Maintainer tool: regenerate explainer/data.js from a reference run's WORK/*.json. Run from labs/ after
Steps 1-5 and D1-D2:
    docker compose run --rm workbench python concept-parameters/scripts/export_explainer_data.py
A student's work/ never needs this; the shipped data.js is the reference run.
"""
import json

import labkit

labkit.banner()

import paramlab as pl  # noqa: E402

J = {n: pl.jload(f"{n}.json") for n in ("header", "activations", "edit", "routes", "persistence", "manifest_check",
                                         "runtime")}
missing = [n for n, v in J.items() if v is None]
if missing:
    raise SystemExit(f"[!!] run these steps first, their WORK/*.json is missing: {', '.join(missing)}")
r3 = lambda x: round(x, 3)  # noqa: E731
h, a, e, r, p, m, rt = (J[k] for k in J)
data = {
    "canary": pl.CANARY, "model": h["repo"], "revision": h["revision"][:12],
    "header": {k: h[k] for k in ("files", "pinned_match", "pinned_total", "header_bytes", "tensors", "dtypes",
                                 "params", "data_bytes", "size", "torch_loaded", "tied", "hidden", "layers", "inter")},
    "groups": h["groups"], "block": h["block"], "sha": h["sha"][:12],
    "act": {"prompts": a["prompts"], "tokens": a["tokens"], "same_weights": a["sha"][0] == a["sha"][1],
            "sha": a["sha"][0][:12], "n_act": a["n_act"], "next": a["next"], "repeat": a["repeat"],
            "rel": [r3(x["rel"]) for x in a["rows"]], "norm_a": [round(x["norm_a"], 1) for x in a["rows"]],
            "norm_b": [round(x["norm_b"], 1) for x in a["rows"]]},
    "edit": {"tensor": e["tensor"], "shape": e["shape"], "steps": e["steps"], "rows": e["rows"],
             "loss0": e["loss"][0], "loss1": e["loss"][-1], "changed": e["changed"], "numel": e["tensor_numel"],
             "rel_norm": r3(e["rel_norm"]), "header_same": e["header_same"], "size": e["size"],
             "sha": [s[:12] for s in e["sha"]], "layer": pl.EDIT_LAYER},
    "routes": {"k": r["canary"], "n": r["n"], "same": r["same"], "logit_gap": r["logit_gap"],
               "route_gap": r["route_gap"], "diff": [round(x, 2) for x in r["diff_edit"]], "first": r["first"],
               "sha_same": r["sha_clean"] == r["sha_hooked"], "probe": r["probes"][1],
               "plain": r["plain"][1][:60], "hook": r["hook"][1][:60]},
    "persist": [{"label": x["label"], "k": x["k"], "n": x["n"]} for x in p["rows"]],
    "persist_sha": {k: v[:12] for k, v in p["sha"].items()},
    "manifest": [{"folder": x["folder"], "verdict": x["verdict"], "bad": x["bad"], "loaded": x["loaded"], "k": x["k"]}
                 for x in m["rows"]],
    "runtime": [{"state": x["state"], "audit_ok": x["audit_ok"], "probe_ok": x["probe_ok"], "k": x["k"],
                 "same": x["same"], "verdict": x["verdict"],
                 "finding": "; ".join(f"{w} {kind}" for w, kind, _ in x["findings"])} for x in rt["rows"]],
    "modules": rt["modules"],
}
out = labkit.inp("explainer/data.js")
out.write_text("/* LAB-39 concept-parameters reference run, exported by scripts/export_explainer_data.py. */\n"
               f"window.LAB_DATA = {json.dumps(data, indent=1, ensure_ascii=False)};\n")
print(f"[ok] wrote {labkit.node_id()}/explainer/data.js ({out.stat().st_size:,} bytes)")
