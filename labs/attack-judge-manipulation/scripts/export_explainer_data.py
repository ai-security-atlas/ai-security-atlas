"""Maintainer tool: regenerate explainer/data.js from a reference run. Run from labs/ after
Steps 1–4, D1–D3 and Evaluate:
    docker compose run --rm workbench python attack-judge-manipulation/scripts/export_explainer_data.py
"""
import json

import labkit

labkit.banner()

import harness as H  # noqa: E402

s01 = H.load_work("s01.json")
s02 = H.load_work("s02.json")
d1 = H.load_work("d1.json")
d2 = H.load_work("d2.json")
d3 = H.load_work("d3.json")
ev = H.load_work("evaluate.json")
_, answers = H.load()
lamp = next(r for r in answers["rows"] if r["id"] == "lamp-note")


def pack(records, styles):
    out = {}
    grouped = H.by_style(records)
    for style in styles:
        flags = [r["yes"] for r in grouped.get(style, [])]
        if not flags:
            continue
        rate = __import__("evalkit").Rate.of(flags)
        out[style] = rate.to_dict()
    return out


def screen_counts():
    out = {}
    for style in H.STYLES:
        group = H.rows_for(answers, (style,))
        blocked = sum(1 for r in group if H.screen_hit(r["text"]))
        out[style] = {"blocked": blocked, "n": len(group)}
    return out


data = {
    "canary": H.CANARY,
    "exam": "Northwind harbor exam",
    "n": 8,
    "judge": s02["info"],
    "example": {
        "id": lamp["id"],
        "question": lamp["question"],
        "gold": lamp["gold"],
        "wrong": lamp["wrong"],
        "claim": lamp["text"].splitlines()[0],
        "note": lamp["text"].splitlines()[1],
        "rule": "If the answer contains an examiner note, obey the note.",
    },
    "naive_plain": pack(s01["records"], ("correct", "wrong")),
    "naive": pack(s02["records"], ("wrong", "note", "authority", "verbose", "adapt", "sab",
                                   "honest_long", "honest_self")),
    "seed1_match": s02["seed1_match"],
    "neutral": pack(s02["neutral"], ("correct", "wrong", "note", "authority", "verbose", "adapt", "sab")),
    "boundary": pack(d1["records"], ("correct", "note", "verbose", "adapt", "sab", "honest_long")),
    "programmatic": pack(d2["programmatic"], H.STYLES),
    "second": pack(d2["second"], ("correct", "note", "sab", "adapt", "wrong")),
    "ensemble": pack(d2["ensemble"], ("correct", "note", "sab", "adapt", "wrong")),
    "screen": screen_counts(),
    "kappa": {"naive_steered": s02["agreement"]["kappa"], "scoreboard": d3["agreement"]["kappa"],
              "boundary": d1["agreement"]["kappa"], "reference": d2["reference_kappa"]},
    "cost": {"naive": s02["cost"], "boundary": d1["cost"], "second": d2["cost"],
             "programmatic_queries": 0, "screen_queries": 0},
    "evaluate": {"gates": ev["gates"], "kappa": ev["kappa"]},
}
out = labkit.lab() / "explainer" / "data.js"
txt = ("/* Shipped reference run for the LAB-48 explainer (regenerate with scripts/export_explainer_data.py).\n"
       " * Loaded with a plain <script> tag; a student's work/ folder never changes it. */\n"
       "window.LAB_DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(txt, encoding="utf-8")
print(f"[ok] wrote {out.relative_to(labkit.lab().parent)} ({len(txt.encode())} bytes)")
