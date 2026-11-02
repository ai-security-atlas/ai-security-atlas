"""Step 3: retrieval with no tenant filter. Run from labs/:
    docker compose run --rm workbench python attack-session-leak/scripts/s03_retrieve.py
"""
import labkit

labkit.banner()

import sleak  # noqa: E402

sleak.note_backend()
row = sleak.retrieval_bug()
sleak.show(row)
body = {"collection": sleak.COLLECTION, "query": sleak.QUESTIONS["night"],
        "principal": sleak.HARBOR, "k": 4, "acl": "none"}
hits = sleak.post("/admin/rag/search", body)["hits"]
for h in hits:
    print(f"  hit={h['doc_id']} tenant={h['tenant']} authorized={sleak.yn(h['authorized'])} "
          f"distance={h['distance']}")
print(f"retrieval: top={row.top} unauth={row.unauth} leak={sleak.yn(row.leak)}")
