"""Step 4: a long conversation overflows the window. Which turns survive each runtime? Run from labs/:
    docker compose run --rm workbench python concept-context/scripts/s04_overflow_chat.py
"""
import time

import labkit

labkit.banner()

import ctxlab as C  # noqa: E402

K = 8   # earlier turns in the overflowing conversation
WORD = "What is my booking word?"
NAMES = {"none": "no cut (8192-token window)", "right": "right (transformers default)",
         "left": "left (truncation_side=left)", "turns": "turns (keep system, drop turns)"}

t0 = time.time()
tok, model = C.load()
rows = []
for pol in ("none", "right", "left", "turns"):
    t1 = time.time()
    packed = [C.truncate(tok, C.messages(q, k=K), pol) for q in C.QUESTIONS + [WORD]]
    ids = [p[0] for p in packed]
    replies = C.generate(tok, model, ids)
    ks = [C.kept(tok, i, q) for i, q in zip(ids[:8], C.QUESTIONS)]
    info = packed[0][1]
    rows.append({"policy": pol, "sent": info["sent"], "kept": info["kept"], "dropped_turns": info["dropped_turns"],
                 "system": sum(k["system"] for k in ks), "booking": sum(k["booking"] for k in ks),
                 "question": sum(k["question"] for k in ks), "marker": sum(map(C.follows, replies[:8])), "n": 8,
                 "replies": replies[:8], "recall": C.BOOKING in replies[8], "recall_reply": replies[8],
                 "secs": round(time.time() - t1)})
budget = C.WINDOW - C.MAX_NEW
print(f"conversation: system prompt + {K} earlier turns (the first holds booking word {C.BOOKING}) + a question")
print(f"request {rows[0]['sent']} tokens, {rows[0]['sent'] - budget} over the {budget}-token budget; "
      f"stored replies start with {C.MARKER}")
print(f"{'policy':<34}{'kept':>5}  {'system':<8}{'turn 1':<8}{'question':<10}{C.MARKER:<8}{'recalls ' + C.BOOKING}")
for r in rows:
    extra = f"  dropped {r['dropped_turns']} oldest turns" if r["dropped_turns"] else ""
    print(f"{NAMES[r['policy']]:<34}{r['kept']:>5}  {r['system']}/{r['n']:<6}{r['booking']}/{r['n']:<6}"
          f"{r['question']}/{r['n']:<8}{r['marker']}/{r['n']:<6}{'yes' if r['recall'] else 'no':<5}{extra}")
for r in rows:
    print(f"   {r['policy']:<6} {WORD!r} -> {r['recall_reply'][:56]!r}")
print(f"({time.time() - t0:.0f}s)")
C.save("s04_overflow_chat.json", {"k": K, "budget": budget, "word": WORD, "rows": rows})
