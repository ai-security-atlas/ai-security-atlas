"""Step 3: a long retrieved document overflows the window. What does each runtime cut? Run from labs/:
    docker compose run --rm workbench python concept-context/scripts/s03_overflow_doc.py
"""
import time

import labkit

labkit.banner()

import ctxlab as C  # noqa: E402

LONG = 8   # paragraphs of the wiki page in the overflowing request
NAMES = {"none": "no cut (8192-token window)", "right": "right (transformers default)",
         "left": "left (truncation_side=left)", "turns": "turns (keep system, drop turns)"}


def sweep(tok, model, n, policies, cache):
    rows = []
    for pol in policies:
        t0 = time.time()
        packed = [C.truncate(tok, C.messages(q, document=C.doc(n)), pol) for q in C.QUESTIONS]
        ids = [p[0] for p in packed]
        key = tuple(map(tuple, ids))
        same = cache.get(key)
        if same is None:
            cache[key] = (pol, C.generate(tok, model, ids))
        src, replies = cache[key]
        ks = [C.kept(tok, i, q) for i, q in zip(ids, C.QUESTIONS)]
        rows.append({"policy": pol, "paragraphs": n, "sent": packed[0][1]["sent"], "kept": packed[0][1]["kept"],
                     "fallback": packed[0][1]["fallback"], "same_as": src if src != pol else None,
                     "system": sum(k["system"] for k in ks), "question": sum(k["question"] for k in ks),
                     "header": sum(k["header"] for k in ks), "marker": sum(map(C.follows, replies)),
                     "n": len(replies), "replies": replies, "secs": round(time.time() - t0)})
    return rows


tok, model = C.load()
cache = {}
fit = sweep(tok, model, 2, ["none"], cache)[0]
print(f"document 2 paragraphs: request {fit['sent']} tokens, fits in {C.WINDOW - C.MAX_NEW}; "
      f"replies with {C.MARKER}: {fit['marker']}/{fit['n']}   ({fit['secs']}s)")
rows = sweep(tok, model, LONG, ["none", "right", "left", "turns"], cache)
over = rows[0]["sent"] - (C.WINDOW - C.MAX_NEW)
print(f"document {LONG} paragraphs: request {rows[0]['sent']} tokens, {over} over the {C.WINDOW - C.MAX_NEW}-token budget")
print(f"{'policy':<34}{'kept':>5}  {'system':<8}{'question':<10}{C.MARKER:<8}reply to {C.QUESTIONS[0]!r}")
for r in rows:
    note = f"   (same tokens as {r['same_as']}: nothing to drop)" if r["same_as"] else f"   ({r['secs']}s)"
    print(f"{NAMES[r['policy']]:<34}{r['kept']:>5}  {r['system']}/{r['n']:<6}{r['question']}/{r['n']:<8}"
          f"{r['marker']}/{r['n']:<6}{r['replies'][0][:44]!r}{note}")
C.save("s03_overflow_doc.json", {"budget": C.WINDOW - C.MAX_NEW, "fit": fit, "long": LONG, "over": over, "rows": rows})
