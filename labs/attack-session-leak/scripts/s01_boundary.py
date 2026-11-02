"""Step 1: two shops, one assistant, each private code stays with its owner. Run from labs/:
    docker compose run --rm workbench python attack-session-leak/scripts/s01_boundary.py
"""
import labkit

labkit.banner()

import sleak  # noqa: E402

sleak.note_backend()
info = sleak.get("/admin/rag")
want = {sleak.COPPER, sleak.HARBOR}
found = [p for p in info["principals"] if p["id"] in want]
for p in found:
    print(f"principal={p['id']} tenant={p['tenant']} company={p['company']} key_set={'yes' if p.get('key') else 'no'}")
docs = sleak.get(f"/admin/rag/docs?collection={sleak.COLLECTION}")
for d in docs:
    flag = "shared" if d["shared"] else "private"
    print(f"doc={d['id']} tenant={d['tenant']} {flag}")
print("baseline cache=principal acl=pre memory=bound")
rows = sleak.baseline()
for row in rows:
    sleak.show(row)
print(f"baseline: copperleaf canary={sleak.yn(rows[0].canary)} "
      f"harbor leak={sleak.yn(rows[1].leak)} harbor marker={sleak.yn(rows[2].marker)}")
