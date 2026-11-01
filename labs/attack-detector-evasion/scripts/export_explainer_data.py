"""Maintainer tool: regenerate explainer/data.js from a reference run. Run from labs/ after
Steps 1-6, D1, D2, D3 and Evaluate have written work/:
    docker compose run --rm workbench python attack-detector-evasion/scripts/export_explainer_data.py
Step 6 is optional; a missing chat file is recorded as not run.
"""
import json

import labkit

labkit.banner()

import evlab  # noqa: E402

s1 = evlab.read("s01_detectors.json", "Step 1")
s2 = evlab.read("s02_characters.json", "Step 2")
s3 = evlab.read("s03_search.json", "Step 3")
s4 = evlab.read("s04_saliency.json", "Step 4")
s5 = evlab.read("s05_function.json", "Step 5")
chat_path = labkit.work() / "s06_chat.json"
chat = json.loads(chat_path.read_text(encoding="utf-8")) if chat_path.exists() else {"ran": False}
d1 = evlab.read("d1_canonicalize.json", "Step D1")
d2 = evlab.read("d2_retrain.json", "Step D2")
d3 = evlab.read("d3_boundary.json", "Step D3")
ev = evlab.read("evaluate.json", "Evaluate")

evaded = next((r for r in s3["rows"] if r["evaded"]), None)
data = {
    "canary": evlab.CANARY,
    "guard": {"repo": s1["repo"], "rev": s1["rev"], "params_m": s1["params_m"], "threshold": s1["threshold"],
              "layers": s1["layers"], "hidden": s1["hidden"]},
    "linear": {"train_n": s1["train_n"], "train_pos": s1["train_pos"], "features": s1["features"],
               "inj": s1["linear_inj"], "ben": s1["linear_ben"]},
    "neural": {"inj": s1["neural_inj"], "ben": s1["neural_ben"]},
    "budget": s1["budget"],
    "chars": {"rows": [{k: r[k] for k in ("name", "neural", "linear", "functional", "n", "example")}
                       for r in s2["rows"]]},
    "search": {"evaded": s3["evaded"], "n": s3["n"], "median_queries": s3["median_queries"],
               "min_queries": s3["min_queries"], "max_queries": s3["max_queries"],
               "functional_evaded": s3["functional_evaded"], "budget": s3["budget"],
               "paraphrase_evaded": s3["paraphrase"]["evaded"], "paraphrase_queries": s3["paraphrase"]["queries"],
               "n_paraphrases": s3["n_paraphrases"],
               "example": evaded["text"] if evaded else "",
               "example_queries": evaded["queries"] if evaded else 0,
               "example_phase": evaded["phase"] if evaded else ""},
    "saliency": {"flipped": s4["flipped"], "n": s4["n"], "neural_flagged": s4["neural_flagged"],
                 "functional_flipped": s4["functional_flipped"], "median_evals": s4["median_evals"],
                 "example_from": next((r["source"] for r in s4["rows"] if r["evaded"]), ""),
                 "example_to": next((r["text"] for r in s4["rows"] if r["evaded"]), ""),
                 "example_swaps": next((r["swaps"] for r in s4["rows"] if r["evaded"]), [])},
    "function": {"released": s5["released"], "n": s5["n"], "boundary_released": s5["boundary_released"],
                 "marker_blocked": s5["marker_blocked"], "warranty_ok": s5["warranty_ok"]},
    "chat": chat,
    "d1": {"rows": [{k: r[k] for k in ("name", "raw", "norm", "n", "restored")} for r in d1["rows"]],
           "benign_changed": d1["benign_changed"], "benign_n": d1["benign_n"], "norm_ms": d1["norm_ms"],
           "unchanged_ops": d1["unchanged_ops"]},
    "d2": {"added": d2["added"], "train_before": d2["train_before"], "train_after": d2["train_after"],
           "fpr_before": d2["fpr_before"], "fpr_after": d2["fpr_after"], "benign_n": d2["benign_n"],
           "ops": d2["ops"], "adaptive_flipped": d2["adaptive_flipped"], "adaptive_n": d2["adaptive_n"],
           "adaptive_neural_flagged": d2["adaptive_neural_flagged"],
           "heldout_safe_before": d2["heldout_safe_before"], "heldout_safe_after": d2["heldout_safe_after"],
           "heldout_n": d2["heldout_n"]},
    "d3": {"detector_released": d3["detector_released"], "boundary_released": d3["boundary_released"],
           "n": d3["n"], "warranty_kept": d3["warranty_kept"], "marker_blocked": d3["marker_blocked"]},
    "evaluate": ev["got"],
}
out = labkit.lab() / "explainer" / "data.js"
txt = ("/* Shipped reference run for the LAB-36 explainer (regenerate with scripts/export_explainer_data.py).\n"
       " * Loaded with a plain <script> tag; a student's work/ folder never changes it. */\n"
       "window.LAB_DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(txt, encoding="utf-8")
print(f"[ok] wrote {out.relative_to(labkit.lab().parent)} ({len(txt.encode())} bytes)")
