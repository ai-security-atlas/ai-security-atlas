"""Maintainer tool: regenerate explainer/data.js from a reference container run. Run from labs/ after
Steps 1-6, D1, D3 and Evaluate, all writing to the same WORK folder:
    docker compose run --rm workbench python concept-decoding/scripts/export_explainer_data.py
Writes explainer/data.js (window.LAB_DATA). Never run by students.
"""
import json

import labkit

labkit.banner()

import declab  # noqa: E402

s1 = declab.read("s01_knobs.json", "Step 1")
s2 = declab.read("s02_greedy_vs_sampled.json", "Step 2")
s3 = declab.read("s03_fork.json", "Step 3")
s4 = declab.read("s04_sweep.json", "Step 4")
s5 = declab.read("s05_one_run.json", "Step 5")
s6 = declab.read("s06_stop_strings.json", "Step 6")
d1 = declab.read("d1_pin_params.json", "Step D1")
d3 = declab.read("d3_validate_output.json", "Step D3")
ev = declab.read("evaluate.json", "Evaluate")

r3 = lambda x: round(x, 3)  # noqa: E731
data = {
    "canary": declab.CANARY,
    "model": s1["model"],
    "ask": s1["ask"],
    "knobs": {"greedy": s1["greedy"], "prefix": s1["prefix"], "entropy": s1["entropy"], "temps": s1["temps"],
              "top": [[t, [r3(p) for p in ps]] for t, ps in s1["top"]], "kept": s1["kept"], "runs": s1["runs"]},
    "greedy": {"k": s2["greedy_rate"]["k"], "n": s2["greedy_rate"]["n"], "refusals": s2["refusals"],
               "replies": s2["greedy"]},
    "sampled": {"T": s2["T"], "n": s2["n"], "rate": s2["sampled_rate"], "per_ask": s2["per_ask"],
                "cells": [1 if declab.leaks(x) else (2 if declab.validator(x) else 0) for x in s2["samples"]],
                "examples": s2["examples"], "variants": s2["variants"][:2]},
    "fork": {"prefix": s3["prefix"], "greedy": s3["greedy"], "leak": s3["leak"], "temps": s3["temps"],
             "greedy_tok": s3["fork"]["greedy"]["token"], "leak_tok": s3["fork"]["leak"]["token"],
             "p_greedy": [r3(p) for p in s3["fork"]["greedy"]["p"]], "p_leak": [r3(p) for p in s3["fork"]["leak"]["p"]],
             "rank": s3["rank"], "nucleus": s3["nucleus"],
             "tail": [r3(s3["path"][str(t)]["tail"]) for t in s3["temps"]]},
    "sweep": {"n": s4["n"], "rows": [{k: r[k] for k in ("setting", "T", "k", "n", "p", "lo", "hi", "distinct")}
                                     for r in s4["rows"]]},
    "one_run": {"cols": s5["columns"], "zero": s5["zero_passes"], "n95": s5["n95"], "first": s5["first"],
                "max": s5["max"], "replay": s5["replay"]},
    "stop": {"T": s6["T"], "n": s6["n"], "bare": s6["bare_tok"][:4], "ctx": s6["ctx_tok"][:4],
             "rows": [{"rule": r["rule"], "k": r["k"], "any": r["any_spelling"]} for r in s6["rows"]],
             "cut": s6["cut_example"], "slip": s6["slip_example"]},
    "pin": {"search": d1["search"], "first": d1["first"], "pass_replay": d1["pass_replay"], "pinned": d1["pinned"],
            "pinned_replay": d1["pinned_replay"], "reply": d1["reply"], "decodes": d1["decodes"]},
    "validate": {"rows": d3["rows"], "sizes": d3["sizes"]},
    "evaluate": ev["got"],
}
out = labkit.lab() / "explainer" / "data.js"
txt = ("/* Shipped reference run for the LAB-28 explainer (regenerate with scripts/export_explainer_data.py).\n"
       " * Loaded with a plain <script> tag; a student's work/ folder never changes it. */\n"
       "window.LAB_DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
out.write_text(txt)
print(f"[ok] wrote {out.relative_to(labkit.lab().parent)} ({len(txt.encode())} bytes)")
