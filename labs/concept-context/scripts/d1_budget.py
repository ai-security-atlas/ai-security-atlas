"""Step D1: count tokens before the call; trim by priority and log it, or reject. Run from labs/:
    docker compose run --rm workbench python concept-context/scripts/d1_budget.py
"""
import time

import labkit

labkit.banner()

import ctxlab as C  # noqa: E402

DOC_N, CHAT_K = 8, 8   # the overflowing requests of Steps 3 and 4
t0 = time.time()
tok, model = C.load()
budget = C.WINDOW - C.MAX_NEW
print(f"budget {budget} tokens: system prompt and question pinned, document trimmed by paragraph, "
      f"then oldest turns dropped")
rows = []
for name, kw in ((f"Step 3 request ({DOC_N}-paragraph document)", {"n_doc": DOC_N}),
                 (f"Step 4 request ({CHAT_K} earlier turns)", {"k": CHAT_K})):
    log = []
    ids = [C.budgeted(tok, q, log=log, **kw)[0] for q in C.QUESTIONS]
    replies = C.generate(tok, model, ids)
    ks = [C.kept(tok, i, q) for i, q in zip(ids, C.QUESTIONS)]
    rows.append({"request": name, "tokens": max(map(len, ids)), "system": sum(k["system"] for k in ks),
                 "question": sum(k["question"] for k in ks), "marker": sum(map(C.follows, replies)), "n": len(ids),
                 "events": log[0]["events"], "replies": replies})
print(f"{'request':<38}{'tokens':>6}  {'system':<8}{'question':<10}{C.MARKER:<8}logged event")
for r in rows:
    print(f"{r['request']:<38}{r['tokens']:>6}  {r['system']}/{r['n']:<6}{r['question']}/{r['n']:<8}"
          f"{r['marker']}/{r['n']:<6}{'; '.join(r['events'])}")
print(f"   e.g. {rows[0]['replies'][0][:60]!r}")
big = "Please read this whole page and answer: " + C.doc()
try:
    C.budgeted(tok, big)
    reject = "accepted"
except C.Overflow as e:
    reject = str(e)
print(f"a user message that alone is too long ({C.count(tok, big)} tokens): {reject}")
print(f"({time.time() - t0:.0f}s)")
C.save("d1_budget.json", {"budget": budget, "rows": rows, "reject": reject, "big_tokens": C.count(tok, big)})
