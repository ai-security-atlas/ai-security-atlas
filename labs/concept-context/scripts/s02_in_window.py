"""Step 2: the model works only from what is in the window. Run from labs/:
    docker compose run --rm workbench python concept-context/scripts/s02_in_window.py
"""
import time

import labkit

labkit.banner()

import ctxlab as C  # noqa: E402

t0 = time.time()
tok, model = C.load()
document = C.doc(2)
reqs = [C.ids_of(tok, C.messages(q, k=1, document=document, tool=C.TOOL)) for q in C.QUESTIONS]
LAST = "How long is the crossing?"
WORD = "What is my booking word?"
probes = [("crossing time, with the document", C.messages(LAST, document=document)),
          ("crossing time, no document", C.messages(LAST)),
          ("booking word, with the earlier turn", C.messages(WORD, k=1)),
          ("booking word, new request", C.messages(WORD))]
rule = C.generate(tok, model, reqs)
probe_replies = C.generate(tok, model, [C.ids_of(tok, m) for _, m in probes], max_new=40)
k = sum(map(C.follows, rule))
print(f"Step 1 request ({len(reqs[0])} tokens, fits): replies that start with {C.MARKER}: {k}/{len(rule)}")
for q, r in list(zip(C.QUESTIONS, rule))[:3]:
    print(f"   {q!r:<34} -> {r[:60]!r}")
rows = []
print(f"{'request':<38}{'answer has':<14}reply")
for (name, _), r, wants in zip(probes, probe_replies, (["35", "thirty-five"],) * 2 + ([C.BOOKING.lower()],) * 2):
    found = [w for w in wants if w in r.lower()]
    hit = bool(found)
    i = r.lower().find(found[0]) if hit else 0
    shown = (("..." if i > 30 else "") + r[max(0, i - 30):i + 30]) if hit else r[:60]
    rows.append({"request": name, "want": wants[0], "found": found[0] if hit else None, "reply": r})
    print(f"{name:<38}{(r[i:i + len(found[0])] if hit else '-'):<14}{shown!r}")
hits = [r["found"] is not None for r in rows]
if hits == [True, False, True, False]:
    print(f"the facts come back only when the window holds them   {C.secs(t0)}")
else:
    print(f"[!!] window and answers do not line up {hits}   {C.secs(t0)}")
C.save("s02_in_window.json", {"tokens": len(reqs[0]), "rule_k": k, "rule_n": len(rule),
                              "rule": [{"q": q, "reply": r} for q, r in zip(C.QUESTIONS, rule)], "probes": rows})
