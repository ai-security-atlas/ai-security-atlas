"""Maintainer tool: regenerate explainer/data.js from a reference container run. Run from labs/ after
Steps 1-5, D1, D2 and Evaluate, all writing to the same work/ folder:
    docker compose run --rm workbench python arch-encoder/scripts/export_explainer_data.py
Writes explainer/data.js (window.LAB_DATA). Never run by students.
"""
import json

import labkit

labkit.banner()

import enclab  # noqa: E402

s1 = enclab.read("s01_guardrail.json", "Step 1")
s2 = enclab.read("s02_both_ways.json", "Step 2")
s3 = enclab.read("s03_position.json", "Step 3")
s4 = enclab.read("s04_perturb.json", "Step 4")
s5 = enclab.read("s05_summarizer.json", "Step 5")
d1 = enclab.read("d1_windows.json", "Step D1")
d2 = enclab.read("d2_normalize.json", "Step D2")
ev = enclab.read("evaluate.json", "Evaluate")

hits = [r for r in s5["rows"] if r["canary"]]
data = {
    "canary": enclab.CANARY,
    "guard": {k: s1[k] for k in ("repo", "rev", "model_type", "layers", "hidden", "params_m", "labels", "max_len")},
    "short": {"rows": [{"kind": r["kind"], "text": r["text"], "p": round(r["p"], 3)} for r in s1["rows"]],
              "tp": s1["tp"], "n_inj": s1["n_inj"], "fp": s1["fp"], "n_ben": s1["n_ben"],
              "fp_text": next((r["text"] for r in s1["rows"] if r["kind"] == "benign" and r["p"] >= .5), "-")},
    "both": {"a": s2["a"], "b": s2["b"], "rows": s2["rows"]},
    "pos": {"rows": [{k: r[k] for k in ("p", "k", "n", "per_topic")} for r in s3["rows"]], "n_inj": len(enclab.INJECTIONS),
            "clean": {k: round(v, 3) for k, v in s3["clean"].items()}, "ok_topics": s3["ok_topics"],
            "before_ok": s3["before_ok"], "after_ok": s3["after_ok"], "same_max": s3["same_max"], "same_n": s3["same_n"],
            "example": s3["example"]},
    "perturb": {"rows": [{k: r[k] for k in ("name", "k", "n", "tokens", "example")} for r in s4["rows"]],
                "plain_toks": s4["plain_toks"], "glyph_word": s4["glyph_word"], "glyph_toks": s4["glyph_toks"]},
    "summ": {"start": s5["start"], "passed": s5["passed"], "hits": s5["hits"], "clean_hits": s5["clean_hits"],
             "trunc_hits": s5["trunc_hits"], "example": (hits[1] if len(hits) > 1 else hits[0])["summary"] if hits else "-",
             "rows": [{k: r[k] for k in ("topic", "inj", "passed", "canary")} for r in s5["rows"]]},
    "d1": {"positions": d1["positions"], "blocked": d1["blocked"], "n_hits": d1["n_hits"], "adaptive": d1["adaptive"],
           "rows": [{k: r[k] for k in ["method", "clean", "passes"] + [str(p) for p in d1["positions"]]} for r in d1["rows"]]},
    "d2": {"rows": [{k: r[k] for k in ("name", "raw", "norm", "n", "example")} for r in d2["rows"]],
           "benign_same": d2["benign_same"], "docs_same": d2["docs_same"]},
    "evaluate": ev["got"],
}
out = labkit.lab() / "explainer" / "data.js"
txt = ("/* Shipped reference run for the LAB-34 explainer (regenerate with scripts/export_explainer_data.py).\n"
       " * Loaded with a plain <script> tag; a student's work/ folder never changes it. */\n"
       "window.LAB_DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
out.write_text(txt)
print(f"[ok] wrote {out.relative_to(labkit.lab().parent)} ({len(txt.encode())} bytes)")
