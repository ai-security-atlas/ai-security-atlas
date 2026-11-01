"""Maintainer tool: regenerate explainer/data.js from a reference container run. Run from labs/ after
Steps 1-6, D1, D2 and Evaluate, all writing to the same work/ folder:
    docker compose run --rm workbench python arch-embedding/scripts/export_explainer_data.py
Writes explainer/data.js (window.LAB_DATA). Never run by students.
"""
import json

import labkit

labkit.banner()

import emb  # noqa: E402

s1 = emb.read("s01_biencoder.json", "Step 1")
s2 = emb.read("s02_crossencoder.json", "Step 2")
s3 = emb.read("s03_plant.json", "Step 3")
s4 = emb.read("s04_app_index.json", "Step 4")
s5 = emb.read("s05_mirror_dose.json", "Step 5")
s6 = emb.read("s06_invert.json", "Step 6")
d1 = emb.read("d1_rank_controls.json", "Step D1")
d2 = emb.read("d2_vectors.json", "Step D2")
ev = emb.read("evaluate.json", "Evaluate")
C = emb.corpus()
first = C["queries"][0]
w4 = next(r for r in s4["rows"] if r["q"] == first["id"])

data = {
    "canary": emb.CANARY,
    "question": first["text"],
    "gold_text": next(p["text"] for p in C["passages"] if p["id"] == first["gold"]),
    "bi": {k: s1[k] for k in ("repo", "rev", "layers", "hidden", "params_m", "max_len", "n_passages", "n_queries",
                              "top1", "parity_min", "parity_rank", "app_model")} |
          {"vec6": s1["example"]["vec6"], "rows": [{k: r[k] for k in ("q", "cos_gold", "cos_next")} for r in s1["rows"]]},
    "ce": {k: s2[k] for k in ("repo", "rev", "layers", "params_m", "top", "top1", "gold_min", "ms_bi", "ms_ce")} |
          {"pairs": s2["example"]["pairs"]},
    "plant": {"n": s3["n"], "k": s3["k"], "top": s3["top"], "example": s3["example"], "dropped": s3["stuffed_dropped"],
              "kinds": {k: {kk: v[kk] for kk in ("cos1", "rr1", "cosK", "rrK")} |
                        {"ranks": [[r["cos_rank"], r["rr_rank"]] for r in v["rows"]]} for k, v in s3["table"].items()}},
    "app": {k: s4[k] for k in ("n", "p1", "p4", "g4", "c1", "canary_q", "embedder", "chunks")} | {"hits": w4["hits"]},
    "dose": {"rows": s5["rows"], "gold_cos": s5["gold_cos"], "n": s5["n"]},
    "inv": {"n": s6["n"], "row": s6["canary_row"], "true": s6["canary_true"],
            "A": {k: s6["res"]["A"][k] for k in ("n_cand", "exact", "fields", "cos_mean", "canary", "example_wording")},
            "B": {k: s6["res"]["B"][k] for k in ("n_cand", "exact", "fields", "cos_mean", "canary", "example_wording")}},
    "d1": {k: d1[k] for k in ("tau", "clean_min", "k", "n", "rows", "voids", "n_posts")},
    "d2": {k: d2[k] for k in ("probe", "same", "nq", "raw", "blind", "rows", "need", "n")},
    "evaluate": ev["got"],
}
out = labkit.lab() / "explainer" / "data.js"
txt = ("/* Shipped reference run for the LAB-40 explainer (regenerate with scripts/export_explainer_data.py).\n"
       " * Loaded with a plain <script> tag; a student's work/ folder never changes it. */\n"
       "window.LAB_DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
out.write_text(txt)
print(f"[ok] wrote {out.relative_to(labkit.lab().parent)} ({len(txt.encode())} bytes)")
