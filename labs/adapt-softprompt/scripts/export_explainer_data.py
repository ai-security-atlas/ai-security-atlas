"""Maintainer tool: regenerate explainer/data.js from a reference container run. Run from labs/ after
Steps 1-5, D1, D2 and Evaluate, all writing to the same work/ folder:
    docker compose run --rm workbench python adapt-softprompt/scripts/export_explainer_data.py
Writes explainer/data.js (window.LAB_DATA). Never run by students.
"""
import json

import labkit

labkit.banner()

import spl  # noqa: E402


def need(name, step):
    p = labkit.out(name)
    if not p.exists():
        raise SystemExit(f"[!!] {p} missing: run {step} first")
    return json.loads(p.read_text())


s1 = need("s01_task.json", "Step 1")
s2 = need("s02_train.json", "Step 2")
s3 = need("s03_read.json", "Step 3")
s4 = need("s04_prefix.json", "Step 4")
s5 = need("s05_swapped.json", "Step 5")
d1 = need("d1_inspect.json", "Step D1")
d2 = need("d2_acceptance.json", "Step D2")
ev = need("evaluate.json", "Evaluate")
repo, rev = spl.tinylm.MODELS[spl.MODEL]

data = {
    "canary": spl.CANARY, "model": "SmolLM2-135M-Instruct", "repo": repo, "rev": rev[:7],
    "queues": spl.QUEUES, "n_train": len(spl.TRAIN), "n_heldout": len(spl.HELDOUT), "n_virtual": spl.N_VIRTUAL,
    "gate": {"total": spl.GATE_TOTAL, "per_queue": spl.GATE_PER_QUEUE},
    "task": {k: s1[k] for k in ("params", "layers", "hidden", "vocab", "instruction_tokens")} | {
        "none": s1["no instruction"], "written": s1["written instruction"]},
    "soft": {k: s2[k] for k in ("trainable", "frozen", "secs", "train", "heldout", "bytes", "fired")} | {
        "sha": s2["sha256"][:16], "trace": s2["trace"][::3] + [s2["trace"][-1]]},
    "read": {k: s3[k] for k in ("near", "norms", "vocab_norm_median", "vocab_norm_min", "vocab_norm_max",
                                "token_nn_cos_median", "text", "heldout_vectors", "heldout_text")},
    "prefix": {k: s4[k] for k in ("trainable", "bytes", "layers", "kv_shape", "secs", "train", "heldout")},
    "swap": {k: s5[k] for k in ("heldout_true", "heldout_swapped", "fired", "train_swapped", "bytes")} | {
        "sha": s5["sha256"][:16], "config_diff": s5["config_diff"]},
    "d1": {"pin": d1["pin"][:16], "vocab_norm_max": d1["vocab_norm_max"], "norm_flags": d1["norm_flags"],
           "static_same": d1["static_same"], "norm_overlap_swapped": d1["norm_overlap_swapped"],
           "norm_overlap_untrained": d1["norm_overlap_untrained"],
           "rows": {k: {x: r[x] for x in ("norm_min", "norm_max", "max_cos", "pin")} | {"sha": r["sha256"][:12]}
                    for k, r in d1["rows"].items()}},
    "d2": d2,
    "evaluate": ev,
}
out = labkit.lab() / "explainer" / "data.js"
out.write_text("/* Shipped reference run for the LAB-58 explainer (regenerate with scripts/export_explainer_data.py).\n"
               " * Loaded with a plain <script> tag; a student's work/ folder never changes it. */\n"
               "window.LAB_DATA = " + json.dumps(data, indent=1, ensure_ascii=False) + ";\n")
print(f"[ok] wrote {out.relative_to(labkit.lab().parent)} ({out.stat().st_size} bytes)")
