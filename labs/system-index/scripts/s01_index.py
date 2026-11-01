"""Step 1: the shared folder and the index built from it. Run from labs/:
    docker compose run --rm workbench python system-index/scripts/s01_index.py
Lists kb-drop/ as the nightly job saw it, the chunks and metadata atlas-app stored, and the baseline ranking
for the refund question.
"""
import labkit

labkit.banner()

import kb  # noqa: E402

kb.wait_ready()
docs = kb.get(f"/admin/rag/docs?collection={kb.OPEN}")
print(f"kb-drop/ -> collection {kb.OPEN}: {len(docs)} files, chunker 400 chars / 80 overlap")
print(f"  {'file':<26} {'chars':>5} {'chunks':>6}  source written into the index")
for d in docs:
    print(f"  {d['id']:<26} {len(d['text']):>5} {len(d['chunks']):>6}  {d['source']}")
one = kb.search(kb.OPEN, "refund limit", k=1)[0]
print(f"\nmetadata on chunk {one['id']}: tenant={one['tenant']} shared={one['shared']} source={one['source']!r}")
print("writer identity checked at ingest: none (the author line is whatever the file says)")

q = kb.queries()["target"][0]["q"]
hits = kb.search(kb.OPEN, q)
print(f"\nbaseline top-{kb.K} for {q!r}:")
print(f"  {'rank':<5} {'distance':<9} {'chunk':<26} text")
for i, h in enumerate(hits, 1):
    print(f"  {i:<5} {h['distance']:<9.4f} {h['id']:<26} {kb.short(h['text'], 52)}")
Q = kb.queries()
base = {x["id"]: [h["id"] for h in kb.search(kb.OPEN, x["q"])] for x in Q["target"] + Q["control"]}
kb.save("index.json", {"baseline": base, "docs": [{"id": d["id"], "chars": len(d["text"]), "chunks": len(d["chunks"]),
                                 "source": d["source"], "title": d["title"]} for d in docs],
                       "query": q, "hits": [{k: h[k] for k in ("id", "doc_id", "distance", "text", "source")}
                                            for h in hits]})
