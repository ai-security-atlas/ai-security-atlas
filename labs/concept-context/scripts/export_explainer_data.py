"""Maintainer tool: regenerate explainer/data.js from a reference container run. Run from labs/ after Steps 1-6,
D1, D2 and Evaluate, all writing to the same WORK folder (Step 5 needs the model backend):
    docker compose run --rm workbench python concept-context/scripts/export_explainer_data.py
Writes explainer/data.js (window.LAB_DATA). Never run by students.
"""
import json

import labkit

labkit.banner()

import ctxlab as C  # noqa: E402

s1 = C.read("s01_assemble.json", "Step 1")
s2 = C.read("s02_in_window.json", "Step 2")
s3 = C.read("s03_overflow_doc.json", "Step 3")
s4 = C.read("s04_overflow_chat.json", "Step 4")
s5 = C.read("s05_ollama.json", "Step 5")
s6 = C.read("s06_few_shot.json", "Step 6")
d1 = C.read("d1_budget.json", "Step D1")
d2 = C.read("d2_policy_in_code.json", "Step D2")
ev = C.read("evaluate.json", "Evaluate")

pick = lambda r, keys: {k: r[k] for k in keys}  # noqa: E731
tok = C.load()[0]


def plain(msgs):
    return len(tok.apply_chat_template(msgs, tokenize=True, return_dict=False))


def spans(msgs, q):
    """[(piece, tokens)] of a request in window order, for the explainer's token bars."""
    out = [("system", plain(msgs[:1]))]
    for i in range(1, len(msgs) - 1, 2):
        out.append(("turn", plain(msgs[:i + 2]) - plain(msgs[:i])))
    user = plain(msgs) - plain(msgs[:-1])
    qn = C.count(tok, q) + 4
    if len(msgs[-1]["content"]) > len(q):
        out.append(("document", user - qn))
    out.append(("question", qn))
    out.append(("header", len(C.ids_of(tok, msgs)) - plain(msgs)))
    return out


q0 = C.QUESTIONS[0]
data = {
    "canary": C.CANARY, "marker": C.MARKER, "booking": C.BOOKING,
    "assemble": pick(s1, ("model", "trained", "window", "max_new", "budget", "pieces", "total", "grow")),
    "in_window": {"tokens": s2["tokens"], "rule_k": s2["rule_k"], "rule_n": s2["rule_n"],
                  "example": s2["rule"][0], "probes": [pick(p, ("request", "found", "reply")) for p in s2["probes"]]},
    "doc": {"spans": spans(C.messages(q0, document=C.doc(s3["long"])), q0), "budget": s3["budget"], "long": s3["long"], "over": s3["over"],
            "fit": pick(s3["fit"], ("sent", "marker", "n")),
            "rows": [dict(pick(r, ("policy", "sent", "kept", "system", "question", "marker", "n", "same_as")),
                          reply=r["replies"][0]) for r in s3["rows"]]},
    "chat": {"spans": spans(C.messages(q0, k=s4["k"]), q0), "k": s4["k"], "budget": s4["budget"], "word": s4["word"],
             "rows": [pick(r, ("policy", "sent", "kept", "dropped_turns", "system", "booking", "question", "marker",
                               "n", "recall", "recall_reply")) for r in s4["rows"]]},
    "ollama": {"version": s5["ollama"], "model": s5["model"], "digest": s5["digest"], "k": s5["k"],
               "v1_context": s5["v1_context"],
               "rows": [pick(r, ("shape", "num_ctx", "prompt_tokens", "marker", "n", "name", "name_reply", "recall"))
                        for r in s5["rows"]]},
    "few_shot": {"flip": s6["flip"], "example": s6["example"], "review": C.NEG[0],
                 "rows": [pick(r, ("cond", "labels", "correct", "outside", "canary", "n")) for r in s6["rows"]]},
    "budget": {"rows": [pick(r, ("request", "tokens", "system", "question", "marker", "n", "events"))
                        for r in d1["rows"]], "reject": d1["reject"], "big_tokens": d1["big_tokens"]},
    "code": {"allow": d2["allow"], "served": pick(d2["served"], ("labels", "canary", "correct", "n")),
             "forensic": d2["forensic"], "log_line": d2["log_line"]},
    "evaluate": ev["rows"],
}
out = labkit.lab() / "explainer" / "data.js"
txt = ("/* Shipped reference run for the LAB-46 explainer (regenerate with scripts/export_explainer_data.py).\n"
       " * Loaded with a plain <script> tag; a student's work/ folder never changes it. */\n"
       "window.LAB_DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
out.write_text(txt)
print(f"[ok] wrote {out.relative_to(labkit.lab().parent)} ({len(txt.encode())} bytes)")
