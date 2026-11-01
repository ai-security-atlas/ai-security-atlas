"""Maintainer tool: regenerate explainer/data.js from a reference container run. Run from labs/ after
Steps 1-5, D1, D2 and Evaluate, all writing to the same WORK folder:
    docker compose run --rm workbench python concept-embeddings/scripts/export_explainer_data.py
Writes explainer/data.js (window.LAB_DATA). Never run by students.
"""
import json

import labkit

labkit.banner()

import emblab  # noqa: E402


def need(name, step):
    p = labkit.out(name)
    if not p.exists():
        raise SystemExit(f"[!!] {p} missing: run {step} first")
    return json.loads(p.read_text())


s1 = need("s01_table.json", "Step 1")
s2 = need("s02_two_vectors.json", "Step 2")
s3 = need("s03_wider_door.json", "Step 3")
s4 = need("s04_soft_prompt.json", "Step 4")
s5 = need("s05_project.json", "Step 5")
d1 = need("d1_text_only.json", "Step D1")
d2 = need("d2_validate.json", "Step D2")
ev = need("evaluate.json", "Evaluate")
cnt = lambda rows, k: sum(r["canary"] for r in rows if r["kind"] == k)

data = {
    "canary": emblab.CANARY, "model": s1["model"].split("/")[1], "n_soft": emblab.N_SOFT,
    "params": s1["params"], "layers": s1["layers"], "shape": s1["shape"], "tied": s1["tied"], "top": s1["top"], "norms": s1["norms"],
    "neighbors": {k.strip(): v[:3] for k, v in s1["neighbors"].items()},
    "rec": {k: s2[k] for k in ("st_model", "dim_in", "dim_rec", "bank_in", "bank_rec", "q_same", "q_other")},
    "door": {"same": s3["same"], "reply": s3["ids_reply"], "far": s3["far_reply"],
             "mix": [{"t": m["t"], "dist": m["dist"], "reply": m["reply"]} for m in s3["mix"]]},
    "soft": {"solved": s4["solved"], "seconds": s4["seconds"], "curve": s4["curve"],
             "train": cnt(s4["rows"], "train"), "held": cnt(s4["rows"], "held-out"),
             "n_train": len(emblab.TRAIN), "n_held": len(emblab.HELDOUT),
             "control": cnt(s4["rows"], "control"),
             "example": next(r for r in s4["rows"] if r["kind"] == "held-out" and r["canary"])["reply"]
             if cnt(s4["rows"], "held-out") else s4["rows"][0]["reply"]},
    "proj": {k: s5[k] for k in ("tokens", "cos", "dist", "text", "same_as_init", "soft_loss", "proj_loss", "forced", "n")},
    "init_loss": s4["curve"][0][1],
    "gate": [{k: r[k] for k in ("policy", "request", "status", "canary")} for r in d1["rows"]],
    "validate": d2,
    "evaluate": ev,
}
out = labkit.lab() / "explainer" / "data.js"
txt = ("/* Shipped reference run for the LAB-25 explainer (regenerate with scripts/export_explainer_data.py).\n"
       " * Loaded with a plain <script> tag; a student's work/ folder never changes it. */\n"
       "window.LAB_DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
out.write_text(txt)
print(f"[ok] wrote {out.relative_to(labkit.lab().parent)} ({len(txt.encode())} bytes)")
