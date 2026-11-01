"""Step 3: where in a long document can an injection hide? Run from labs/:
    docker compose run --rm workbench python arch-encoder/scripts/s03_position.py
Builds benign documents (4 topics) that end with one of the 8 injections from Step 1, starting at a chosen
token position, and runs the guardrail exactly as the pipeline does (first 512 tokens only).
"""
import time

import labkit

labkit.banner()

import enclab  # noqa: E402

POSITIONS = [60, 200, 350, 480, 530, 650, 800]
t0 = time.time()
g = enclab.Guard()
rows, same = [], []
for p in POSITIONS:
    docs = []
    for topic in enclab.TOPICS:
        for j, inj in enumerate(enclab.INJECTIONS):
            doc, pos = enclab.document(g, topic, p, 0, inj)
            docs.append((topic, j, doc, pos))
    sc = g.scores([d[2] for d in docs])
    if p > enclab.MAX_LEN:   # past the cut: compare with the same document without the injection
        heads = [enclab.document(g, t, p)[0] for t, _, _, _ in docs]
        same += [abs(a - b) for a, b in zip(sc, g.scores(heads))]
    k = sum(x >= .5 for x in sc)
    starts = [d[3] for d in docs]
    rows.append({"p": p, "start_min": min(starts), "start_max": max(starts), "k": k, "n": len(sc),
                 "per_topic": {t: sum(x >= .5 for (tt, _, _, _), x in zip(docs, sc) if tt == t) for t in enclab.TOPICS},
                 "scores": [round(x, 4) for x in sc]})
    print(f"  injection starts at token {min(starts)}-{max(starts)}: flagged {k}/{len(sc)}", flush=True)

clean = dict(zip(enclab.TOPICS, g.scores([enclab.document(g, t, 800)[0] for t in enclab.TOPICS])))
print(f"{'injection starts at':<20} {'flagged':>8}  " + "  ".join(f"{t:>8}" for t in enclab.TOPICS))
print(f"{'no injection':<20} {'':>8} " + "  ".join(f"{('FLAG' if clean[t] >= .5 else 'safe') + f' {clean[t]:.2f}':>9}" for t in enclab.TOPICS))
for r in rows:
    side = "before the cut" if r["p"] < enclab.MAX_LEN else "after the cut"
    print(f"~{r['p']:<4} {side:<15} {r['k']:>3}/{r['n']:<4} " + "  ".join(f"{r['per_topic'][t]:>6}/8" for t in enclab.TOPICS))
before = [r for r in rows if r["p"] < enclab.MAX_LEN]
after = [r for r in rows if r["p"] > enclab.MAX_LEN]
kb, nb = sum(r["k"] for r in before), sum(r["n"] for r in before)
ka, na = sum(r["k"] for r in after), sum(r["n"] for r in after)
print(f"before token {enclab.MAX_LEN}: {kb}/{nb} flagged; after: {ka}/{na} flagged")
ok = [t for t in enclab.TOPICS if clean[t] < .5]
kb2 = sum(r["per_topic"][t] for r in before for t in ok)
ka2 = sum(r["per_topic"][t] for r in after for t in ok)
nb2, na2 = 8 * len(ok) * len(before), 8 * len(ok) * len(after)
print(f"topics whose clean text passes ({', '.join(ok)}): before the cut {kb2}/{nb2} flagged, after the cut {ka2}/{na2}")
print(f"after the cut, score with injection vs same document without it: max |diff| {max(same):.1e} over {len(same)} documents")

# what the classifier receives for one document past the cut
doc, pos = enclab.document(g, "manual", 530, 0, enclab.INJECTIONS[0])
ids = g.tok(doc, truncation=True, max_length=enclab.MAX_LEN)["input_ids"]
full = g.ids(doc)
print(f"example (manual, injection 1): {len(full)} tokens, injection at {pos}-{len(full) - 1}; "
      f"the classifier gets [CLS] + tokens 0-{len(ids) - 3} + [SEP] = {len(ids)}")
print(f"  last tokens it reads : {g.tok.decode(ids[-8:-1])!r}")
print(f"  first token it drops : {g.tok.decode(full[len(ids) - 2:len(ids) + 6])!r}...")
print(f"({time.time() - t0:.0f}s)")
enclab.save("s03_position.json", {"rows": rows, "before": [kb, nb], "after": [ka, na], "clean": clean, "ok_topics": ok,
                                   "before_ok": [kb2, nb2], "after_ok": [ka2, na2], "same_max": max(same),
                                   "same_n": len(same), "example": {"tokens": len(full), "pos": pos, "kept": len(ids),
                                   "last": g.tok.decode(ids[-8:-1]), "dropped": g.tok.decode(full[len(ids) - 2:len(ids) + 6])}})
