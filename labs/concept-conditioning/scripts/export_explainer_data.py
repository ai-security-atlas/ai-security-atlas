"""Maintainer tool: regenerate explainer/data.js from a reference container run. Run from labs/ after
Steps 1-6, D1, D2 and Evaluate, all writing to the same WORK folder:
    docker compose run --rm workbench python concept-conditioning/scripts/export_explainer_data.py
Writes explainer/data.js (window.LAB_DATA). Never run by students.
"""
import json

import labkit

labkit.banner()

import cclab  # noqa: E402


def need(name, step):
    p = labkit.out(name)
    if not p.exists():
        raise SystemExit(f"[!!] {p} missing: run {step} first")
    return json.loads(p.read_text())


s1 = need("s01_encode.json", "Step 1")
s2 = need("s02_neighbors.json", "Step 2")
s3 = need("s03_keyword.json", "Step 3")
s4 = need("s04_truncation.json", "Step 4")
s5 = need("s05_rows.json", "Step 5")
s6 = need("s06_search.json", "Step 6")
d1 = need("d1_embedding_filter.json", "Step D1")
d2 = need("d2_same_view.json", "Step D2")
ev = need("evaluate.json", "Evaluate")

data = {
    "canary": cclab.CANARY, "model": "CLIP ViT-B/32 text tower", "repo": s1["repo"], "rev": s1["rev"],
    "enc": {k: s1[k] for k in ("params", "vocab", "layers", "width", "ctx", "prompt", "tokens", "slots", "rows",
                               "pooled", "lower_same", "long_tokens")},
    "nb": {"cos": dict(list(s2["cos"].items())[:6]), "others": s2["others"], "probe": s2["probe"], "above09": s2["above09"]},
    "kw": {"pattern": s3["pattern"], "n_fox": s3["n_fox"], "n_benign": s3["n_benign"], "kw_fox": s3["kw_fox"],
           "kw_benign": s3["kw_benign"], "passed": s3["passed"], "landed": s3["landed"],
           "rows": [{k: r[k] for k in ("text", "kind", "keyword", "probe", "fox")} for r in s3["rows"] if r["kind"] == "fox"]},
    "trunc": {k: s4[k] for k in ("n_scene", "n_full", "same_ids", "diff", "keyword", "std_probe", "chunks",
                                 "chunk_rows", "chunk_probe", "tail_text")},
    "rows": {k: s5[k] for k in ("a", "b", "pos", "eos", "same", "differ", "pad", "scrub_fox", "scrub_dog", "unscrub", "pad_cos")},
    "row_cos": s5["cos"],
    "search": {k: s6[k] for k in ("n_words", "seconds", "landed", "blocked", "hits", "strong", "threshold", "ties",
                                 "noise", "noise_n", "margin")},
    "d1": {k: d1[k] for k in ("n_fox", "n_benign", "filters", "fps", "miss", "miss_probe", "search_caught", "search_n",
                              "long_one_pass")},
    "d2": d2,
    "evaluate": ev,
}
out = labkit.lab() / "explainer" / "data.js"
txt = ("/* Shipped reference run for the LAB-51 explainer (regenerate with scripts/export_explainer_data.py).\n"
       " * Loaded with a plain <script> tag; a student's work/ folder never changes it. */\n"
       "window.LAB_DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
out.write_text(txt)
print(f"[ok] wrote {out.relative_to(labkit.lab().parent)} ({len(txt.encode())} bytes)")
