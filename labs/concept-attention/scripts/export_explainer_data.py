"""Maintainer tool: regenerate explainer/data.js from a reference container run. Run from labs/ after
Steps 1-5, D1, D2 and Evaluate, all writing to the same WORK folder:
    docker compose run --rm workbench python concept-attention/scripts/export_explainer_data.py
Writes explainer/data.js (window.LAB_DATA). Never run by students.
"""
import json

import labkit

labkit.banner()

import attnlab as A  # noqa: E402


def need(name, step):
    p = labkit.out(name)
    if not p.exists():
        raise SystemExit(f"[!!] {p} missing: run {step} first")
    return json.loads(p.read_text())


s1 = need("s01_capture.json", "Step 1")
s2 = need("s02_one_softmax.json", "Step 2")
s3 = need("s03_sink.json", "Step 3")
s4 = need("s04_distraction.json", "Step 4")
s5 = need("s05_followed.json", "Step 5")
d1 = need("d1_detector.json", "Step D1")
d2 = need("d2_adaptive.json", "Step D2")
ev = need("evaluate.json", "Evaluate")

ex = {e[0]: e for e in s5["examples"]}
data = {
    "canary": A.CANARY,
    "model": A.MODEL_ID.split("/")[1],
    "system": A.SYSTEM,
    "layers": s1["layers"], "heads": s1["heads"], "kv_heads": s1["kv_heads"], "sdpa": s1["sdpa"],
    "capture": {"fixture": s1["fixture"], "middle": s1["middle"], "n": s1["n_tokens"], "counts": s1["counts"],
                "pieces": s1["pieces"], "seg": s1["seg"], "w": [round(x, 4) for x in s1["last_mean"]],
                "top": s1["top"]},
    "softmax": s2["table"],
    "sink": {k: s3[k] for k in ("first", "layer", "gen_mean", "heavy_heads", "clean", "inject", "shift")},
    "distract": {"all": s4["all_heads"], "sel": s4["selected"], "grid": s4["grid"], "top": s4["top"],
                 "bands": s4["bands"], "rise_bands": s4["rise_bands"],
                 "sel_heads": s4["heads"], "rising": s4["rising"], "pair_head": s4["pair"]["head"],
                 "pair": {k: {"w": v["w"], "seg": v["seg"]} for k, v in s4["pair"]["tokens"].items()},
                 "pair_mass": s4["pair"]["mass"]},
    "followed": {"n": s5["followed"], "of": s5["injected"], "clean": s5["clean_followed"],
                 "groups": s5["groups"], "drop_followed": s5["drop_followed"], "drop_ignored": s5["drop_ignored"],
                 "examples": {k: ex[k][2] for k in ("clean-02", "inject-02", "inject-00")}},
    "detector": {"heads": len(d1["heads"]), "t": round(d1["threshold"], 4), "rates": d1["rates"],
                 "all_dev_j": d1["all_dev_j"], "caught": d1["canary_caught"], "canary_test": d1["canary_followed"],
                 "test_scores": d1["test_scores"]},
    "adaptive": {"dev": d2["dev"], "best": d2["best"], "phrasing": d2["phrasing"], "test": d2["test"],
                 "scores": d2["adv_scores"]},
    "evaluate": ev,
}
out = labkit.lab() / "explainer" / "data.js"
txt = ("/* Shipped reference run for the LAB-26 explainer (regenerate with scripts/export_explainer_data.py).\n"
       " * Loaded with a plain <script> tag; a student's work/ folder never changes it. */\n"
       "window.LAB_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n")
out.write_text(txt)
print(f"[ok] wrote {out.relative_to(labkit.lab().parent)} ({len(txt.encode())} bytes)")
