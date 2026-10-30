"""Step 1: the corpus and the chunker. Run from labs/:
    docker compose run --rm workbench python system-rag/scripts/s01_chunk.py
Lists the tenants, principals and documents of the sysrag-kb collection, then cuts Copperleaf's private
agreement into chunks (400 characters, 80 overlap) and shows the metadata each chunk carries.
Writes work/chunks.json.
"""
import json

import labkit

labkit.banner()

import kb  # noqa: E402

info = kb.get("/admin/rag")
print(f"[note] atlas-app {kb.URL}: chunker {info['chunk_size']} chars / {info['chunk_overlap']} overlap, "
      f"embedder {info['embedder']}")
print("principals (from the API key):")
for p in info["principals"]:
    print(f"  {p['id']:<17} tenant {p['tenant'] or '-':<11} roles {','.join(p['roles']) or '-':<14} "
          f"key {p['key'] or '(none)'}")
docs = kb.get(f"/admin/rag/docs?collection={kb.COLLECTION}")
print(f"\ncollection {kb.COLLECTION}: {len(docs)} documents")
for d in docs:
    who = "shared (every caller)" if d["shared"] else f"{d['tenant']} only, roles {','.join(d['roles'])}"
    print(f"  {d['id']:<22} {len(d['text']):>4} chars  {len(d['chunks'])} chunks  {who}")

res = kb.post("/admin/rag/chunk", {"collection": kb.COLLECTION, "doc_id": "copperleaf-agreement"})
print(f"\ncopperleaf-agreement ({res['chars']} chars) -> {len(res['chunks'])} chunks:")
for c in res["chunks"]:
    text = " ".join(c["text"].split())
    flags = [f for f, on in (("CONFIDENTIAL", "CONFIDENTIAL" in text), (kb.CANARY, kb.CANARY in text)) if on]
    print(f"  #{c['i']}  chars {c['start']:>3}-{c['end']:<3}  {kb.short(text, 64)}"
          + (f"  <- {', '.join(flags)}" if flags else ""))
d = next(x for x in docs if x["id"] == "copperleaf-agreement")
print(f"metadata on every chunk: tenant={d['tenant']} shared={d['shared']} roles={','.join(d['roles'])} "
      f"source={d['source']}")
labkit.out("chunks.json").write_text(json.dumps({"info": info, "docs": docs, "copperleaf": res}, indent=1) + "\n")
