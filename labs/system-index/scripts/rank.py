"""Steps 3-4 (read): rank the refund question after a drop. Run from labs/ after restarting atlas-app:
    docker compose run --rm workbench python system-index/scripts/rank.py --label drop
--label names the result file (work/rank_<label>.json). Compares with Step 1's baseline.
"""
import argparse

import labkit

labkit.banner()

import kb  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--label", required=True)
ap.add_argument("--collection", default=kb.OPEN)
a = ap.parse_args()
kb.wait_ready()
base = (kb.load("index.json") or {}).get("baseline", {})
Q = kb.queries()
out = {"collection": a.collection, "queries": {}}
print(f"[note] POST /admin/rag/search collection {a.collection} k={kb.K} (no model call); * = dropped page")
for x in Q["target"] + Q["control"]:
    hits = kb.search(a.collection, x["q"])
    ids = [("*" if kb.is_drop(h) else "") + h["id"] for h in hits]
    row = {"q": x["q"], "kind": "target" if x in Q["target"] else "control", "ids": [h["id"] for h in hits],
           "dist": [h["distance"] for h in hits], "texts": [h["text"] for h in hits], "drop_top1": kb.is_drop(hits[0]),
           "drop_slots": sum(kb.is_drop(h) for h in hits), "rule": any(kb.RULE in h["text"] for h in hits),
           "canary": any(kb.CANARY in h["text"] for h in hits),
           "authors": sorted({kb.claimed(h) for h in hits}), "baseline": base.get(x["id"], [])}
    out["queries"][x["id"]] = row
    print(f"{row['kind']} {x['id']}: {x['q']!r}")
    print(f"  before  {' '.join(row['baseline']) or '(run Step 1 first)'}")
    print(f"  now     {' '.join(ids)}")
    print(f"  dropped page rank 1: {'yes' if row['drop_top1'] else 'no'} · dropped slots {row['drop_slots']}/{kb.K}"
          f" · refund rule in top-{kb.K}: {'yes' if row['rule'] else 'no'} · canary in top-{kb.K}: "
          f"{'yes' if row['canary'] else 'no'} · authors {','.join(row['authors'])}")
T = [r for r in out["queries"].values() if r["kind"] == "target"]
C = [r for r in out["queries"].values() if r["kind"] == "control"]
n = len(T)
print(f"target questions: dropped page rank 1 in {sum(r['drop_top1'] for r in T)}/{n}, "
      f"dropped slots {sum(r['drop_slots'] for r in T)}/{n * kb.K}, refund rule kept in {sum(r['rule'] for r in T)}/{n}")
print(f"control questions with a dropped page in top-{kb.K}: {sum(r['drop_slots'] > 0 for r in C)}/{len(C)}")
kb.save(f"rank_{a.label}.json", out)
