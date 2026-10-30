"""Step D1 (first half): authorization-aware retrieval. Run from labs/:
    docker compose run --rm workbench python system-rag/scripts/d1_acl.py
Runs Harbor's two questions through the retriever three ways (no model call):
  none  rank every chunk (Steps 3-5)
  post  rank every chunk, then drop the ones harbor-buyer may not read
  pre   chromadb where-filter from the principal, so only readable chunks are ranked (profile sysrag-acl)
Writes work/acl.json.
"""
import json

import labkit

labkit.banner()

import kb  # noqa: E402

p = kb.get("/admin/rag")["principals"]
harbor = next(x for x in p if x["id"] == "harbor-buyer")
print(f"[note] principal from key {harbor['key']}: tenant {harbor['tenant']}, roles {','.join(harbor['roles'])}")
where = kb.post("/admin/rag/search", {"collection": kb.COLLECTION, "query": "-", "principal": "harbor-buyer",
                                     "acl": "pre", "k": 1})["where"]
print(f"[note] where-filter (pre): {json.dumps(where)}")
out = {}
for qid in ("own-reference", "probe-reference"):
    q = kb.questions()[qid]
    print(f"\n{q['as']} asks ({q['kind']}): {q['text']!r}")
    print(f"  {'acl':<5} {'chunks':<7} {'not allowed':<12} {'canary':<7} ranked chunk ids")
    out[qid] = {}
    for mode in ("none", "post", "pre"):
        hits = kb.search(q["text"], q["as"], mode)
        out[qid][mode] = hits
        bad = sum(not h["authorized"] for h in hits)
        can = any(kb.CANARY in h["text"] for h in hits)
        print(f"  {mode:<5} {len(hits):<7} {bad:<12} {'yes' if can else 'no':<7} {' '.join(h['id'] for h in hits)}")
labkit.out("acl.json").write_text(json.dumps({"where": where, "questions": out}, indent=1) + "\n")
