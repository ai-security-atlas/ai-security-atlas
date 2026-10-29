"""Maintainer tool: regenerate explainer/data.js from a reference container run. Run from labs/ after
Steps 1-5, D1 and Evaluate, all writing to the same WORK folder:
    docker compose run --rm workbench python concept-logits/scripts/export_explainer_data.py
Writes explainer/data.js (window.LAB_DATA). Never run by students.
"""
import json
import math

import labkit

labkit.banner()

import logitlab  # noqa: E402


def need(name, step):
    p = labkit.out(name)
    if not p.exists():
        raise SystemExit(f"[!!] {p} missing: run {step} first")
    return json.loads(p.read_text())


s1 = need("s01_next_token.json", "Step 1")
s2 = need("s02_detail_levels.json", "Step 2")
s3 = need("s03_which_secret.json", "Step 3")
s4 = need("s04_near_duplicate.json", "Step 4")
s5 = need("s05_hidden_dim.json", "Step 5")
d1 = need("d1_limit_detail.json", "Step D1")
ev = need("evaluate.json", "Evaluate")

sec = {}
for r in s3["results"]:
    if r["secret"] != "A":
        continue
    sec[r["detail"]] = {"found": r["guess"] is not None, "queries": r["queries"]}
    if r["detail"] == "text?":
        sec[r["detail"]]["yes"] = r["yes"]
    if r["detail"] == "topk":
        sec[r["detail"]]["top"] = [[t, round(v, 2)] for t, v in r["top"]]
    if r["detail"] == "full":
        sec[r["detail"]]["pA"], sec[r["detail"]]["pB"] = round(r["pA"], 4), round(r["pB"], 6)

near = []
for i, (name, _, orig, swap, _) in enumerate(logitlab.NEAR_DUPS):
    t, k, f = (s4["results"][d][i] for d in ("text", "topk", "full"))
    near.append({"pair": name, "orig": orig.strip(), "swap": swap.strip(), "text": t["decided"],
                 "topk": k.get("margin"), "topk_seen": k.get("seen", []), "full": f["margin"]})

topk = s2["topk5"]
data = {
    "canary": logitlab.CANARY,
    "secret": logitlab.SECRETS["A"],
    "model": logitlab.MODEL_ID.split("/")[1],
    "hidden": s1["hidden"], "vocab": s1["vocab"],
    "prompt": s1["prompt"],
    "top": s1["top"],                                   # [token, logit, prob, logprob]
    "temps": s1["temps"],
    "levels": {"text": s2["text"]["size"]["chat"], "topk": topk["size"]["chat"],
               "full": s2["full"]["size"]["score"]},
    "redacted": topk["content"],
    "letter_top5": topk["top5"],
    "secret_probe": sec,
    "side_n": s3["side_gap"]["n_per_question"], "side_pyes": s3["side_gap"]["pYes"],
    "near": near, "near_summary": s4["summary"],
    "spectrum": [round(math.log10(max(x, 1e-12)), 3) for x in s5["spectrum"]],
    "spectrum_step": 8, "dim": s5["dim"], "dim_ratio": s5["ratio"],
    "defense": [{"policy": r["policy"], "secret": r["secret"]["A"], "near": r["near_dup"],
                 "hidden": r["hidden"], "ratio": r["ratio"]} for r in d1],
    "evaluate": ev,
}
out = labkit.lab() / "explainer" / "data.js"
txt = ("/* Shipped reference run for the LAB-05 explainer (regenerate with scripts/export_explainer_data.py).\n"
       " * Loaded with a plain <script> tag; a student's work/ folder never changes it. */\n"
       "window.LAB_DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
out.write_text(txt)
print(f"[ok] wrote {out.relative_to(labkit.lab().parent)} ({len(txt.encode())} bytes)")
