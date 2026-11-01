"""Step D2: near-duplicate collapse and a per-source quota in top-k. Run from labs/:
    docker compose run --rm workbench python system-index/scripts/d2_rerank.py
Takes the 12 nearest chunks of the open index for each refund question and re-selects the top 4 under four
rules. The quota keys on the only source the open index has: the author each file declares.
"""
import itertools

import labkit

labkit.banner()

import ingest  # noqa: E402
import kb  # noqa: E402

DEDUP, CANDIDATES = 0.3, 12
RULES = [("plain top-4", {}),
         ("quota 1 per declared author", {"source": kb.claimed, "quota": 1}),
         (f"collapse near-duplicates (J >= {DEDUP})", {"dedup": DEDUP}),
         ("collapse + quota 2 per author", {"dedup": DEDUP, "source": kb.claimed, "quota": 2})]
kb.wait_ready(quiet=True)
drops = [ingest.shingles(ingest.parse(p)["body"]) for p in sorted(ingest.DROPS.glob("*.md"))]
hb = [ingest.shingles(c["text"]) for d in kb.handbook()
      for c in kb.post("/admin/rag/chunk", {"text": d["body"]})["chunks"]]
jd = [ingest.jaccard(a, b) for a, b in itertools.combinations(drops, 2)]
jh = [ingest.jaccard(a, b) for a, b in itertools.combinations(hb, 2)]
print(f"3-word-shingle Jaccard: dropped pages pairwise {min(jd):.2f}-{max(jd):.2f}; "
      f"handbook chunks pairwise max {max(jh):.2f}")
Q = kb.queries()["target"]
cand = {x["id"]: kb.search(kb.OPEN, x["q"], k=CANDIDATES) for x in Q}
n = len(Q)
print(f"[note] {CANDIDATES} candidates per question from {kb.OPEN}, then select {kb.K}")
print(f"{'selection rule':<38} {'dropped slots':<14} {'canary':<7} {'refund rule':<12} {'slots filled':<12} "
      "distinct declared authors")
rows = []
for name, kw in RULES:
    sel = {q: ingest.rerank(h, kb.K, **kw) for q, h in cand.items()}
    r = {"rule": name, "drop_slots": sum(kb.is_drop(h) for s in sel.values() for h in s),
         "canary": sum(any(kb.CANARY in h["text"] for h in s) for s in sel.values()),
         "rule_kept": sum(any(kb.RULE in h["text"] for h in s) for s in sel.values()),
         "filled": sum(len(s) for s in sel.values()),
         "authors": sorted({kb.claimed(h) for s in sel.values() for h in s}),
         "ids": {q: [h["id"] for h in s] for q, s in sel.items()}}
    rows.append(r)
    cells = [f"{r['drop_slots']}/{n * kb.K}", f"{r['canary']}/{n}", f"{r['rule_kept']}/{n}", f"{r['filled']}/{n * kb.K}"]
    print(f"{name:<38} {cells[0]:<14} {cells[1]:<7} {cells[2]:<12} {cells[3]:<12} {len(r['authors'])}")
x = Q[0]["id"]
print(f"\n{Q[0]['q']!r}:")
for r in rows:
    print(f"  {r['rule']:<38} {' '.join(('*' if i.split('#')[0] in kb.DROPPER else '') + i for i in r['ids'][x])}")
kb.save("rerank.json", {"dedup": DEDUP, "candidates": CANDIDATES, "j_drop": [min(jd), max(jd)],
                        "j_handbook_max": max(jh), "rows": rows})
