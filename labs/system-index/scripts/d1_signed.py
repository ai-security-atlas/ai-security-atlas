"""Step D1: signed ingestion with the writer's identity in the index. Run from labs/:
    docker compose run --rm workbench python system-index/scripts/d1_signed.py
1. verifies every file in kb-drop/ the way the plug-in's signed ingestion does (manifest sha256 + HMAC of a
   known writer), 2. audits the open index for chunks no verified writer stands behind, 3. a tamper test in
   memory ($500 -> $5000 in a signed page), 4. the refund questions against sysidx-signed.
"""
import hashlib
import json

import labkit

labkit.banner()

import ingest  # noqa: E402
import kb  # noqa: E402

kb.wait_ready(quiet=True)
ok, bad = ingest.signed_folder()
print(f"signed ingestion of kb-drop/: {len(ok)} accepted, {len(bad)} quarantined")
for d, w in ok:
    print(f"  accept      {d['rel']:<38} writer {w}")
for d, why in bad:
    print(f"  quarantine  {d['rel']:<38} {why} (header says author: {d['author']})")

verified = {d["rel"]: d["body"] for d, _ in ok}
docs = kb.get(f"/admin/rag/docs?collection={kb.OPEN}")
# a chunk passes only if its file path has a verified manifest entry and its text is in that verified file
rel = lambda d: d["source"].removeprefix("kb-drop/").split(" (author: ")[0]  # noqa: E731
chunks = [(rel(d), c) for d in docs for c in d["chunks"]]
unver = [c["id"] for r, c in chunks if c["text"] not in verified.get(r, "")]
print(f"\nforensic audit of {kb.OPEN}: {len(unver)}/{len(chunks)} chunks have no verified writer: {' '.join(unver)}")

keys = json.loads(ingest.KEYS.read_text())["keys"]
ref = next(d for d, _ in ok if d["name"] == "refunds")
raw = (ingest.HANDBOOK / "refunds.md").read_text().replace("$500", "$5000")
fake = dict(ref, sha256=hashlib.sha256(raw.encode()).hexdigest())
_, tamper = ingest.verify(fake, ingest.manifest_entries(), keys)
print(f"tamper test (in memory): handbook/refunds.md with $500 -> $5000: {tamper}")

Q = kb.queries()
res = {"accepted": [d["rel"] for d, _ in ok], "quarantined": [[d["rel"], why] for d, why in bad],
       "unverified_chunks": len(unver), "open_chunks": len(chunks), "tamper": tamper, "queries": {}}
base = (kb.load("index.json") or {}).get("baseline", {})
print(f"\n[note] POST /admin/rag/search collection {kb.SIGNED} k={kb.K}")
for x in Q["target"] + Q["control"]:
    hits = kb.search(kb.SIGNED, x["q"])
    row = {"ids": [h["id"] for h in hits], "drop_slots": sum(kb.is_drop(h) for h in hits),
           "canary": any(kb.CANARY in h["text"] for h in hits), "rule": any(kb.RULE in h["text"] for h in hits),
           "writers": sorted({h["source"] for h in hits}), "as_baseline": [h["id"] for h in hits] == base.get(x["id"])}
    res["queries"][x["id"]] = row
    print(f"  {x['id']:<15} {' '.join(row['ids'])}  canary {'yes' if row['canary'] else 'no'} · "
          f"rule {'yes' if row['rule'] else 'no'} · {', '.join(row['writers'])}")
T = [res["queries"][x["id"]] for x in Q["target"]]
print(f"target questions on {kb.SIGNED}: dropped slots {sum(r['drop_slots'] for r in T)}/{len(T) * kb.K}, "
      f"canary in top-{kb.K} {sum(r['canary'] for r in T)}/{len(T)}, refund rule in top-{kb.K} "
      f"{sum(r['rule'] for r in T)}/{len(T)}")
print(f"rankings identical to Step 1's baseline (before any drop): "
      f"{sum(r['as_baseline'] for r in res['queries'].values())}/{len(res['queries'])}")
kb.save("signed.json", res)
