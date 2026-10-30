"""Step 3: index and retrieval, with no authorization stage. Run from labs/:
    docker compose run --rm workbench python system-rag/scripts/s03_retrieve.py
Queries atlas-app's chromadb index (top 4, cosine distance) as harbor-buyer for an ordinary question and a
probing one, and marks every hit the caller is not allowed to read. No model is called.
Optional: --acl none|pre|post (Step D1). Writes work/retrieve_<acl>.json.
"""
import argparse
import json

import labkit

labkit.banner()

import kb  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--acl", choices=["none", "pre", "post"], default="none")
a = ap.parse_args()

out = {}
print(f"[note] POST {kb.URL}/admin/rag/search collection {kb.COLLECTION} k=4 acl={a.acl} (no model call)")
for qid in ("own-reference", "probe-reference"):
    q = kb.questions()[qid]
    hits = kb.search(q["text"], q["as"], a.acl)
    out[qid] = hits
    print(f"\n{q['as']} asks ({q['kind']}): {q['text']!r}")
    print(f"  rank  distance  chunk                     owner       allowed  canary")
    for r, h in enumerate(hits, 1):
        owner = "shared" if h["shared"] else h["tenant"]
        print(f"  {r:<5} {h['distance']:<9.4f} {h['id']:<25} {owner:<11} {'yes' if h['authorized'] else 'NO':<8} "
              f"{'yes' if kb.CANARY in h['text'] else ''}")
    bad = sum(not h["authorized"] for h in hits)
    print(f"  {len(hits)} chunks retrieved, {bad} the caller may not read"
          + (f"; the canary chunk is rank {next(i for i, h in enumerate(hits, 1) if kb.CANARY in h['text'])}"
             if any(kb.CANARY in h["text"] for h in hits) else ""))
labkit.out(f"retrieve_{a.acl}.json").write_text(json.dumps(out, indent=1) + "\n")
