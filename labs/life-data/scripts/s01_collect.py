"""Step 1: collect the four sources and write one lineage row per record. Run from labs/:
    docker compose run --rm workbench python life-data/scripts/s01_collect.py
Writes work/lineage.json (every record with its source, origin, license, batch and sha256).
"""
import labkit

labkit.banner()

import datalab as L  # noqa: E402

recs = L.collect()
L.jdump("lineage.json", {"records": recs, "sources": L.SOURCES})
print(f"{'source':<12} {'records':>7}  {'supplier':<30} {'license':<22} batch")
for name, s in L.SOURCES.items():
    n = sum(r["source"] == name for r in recs)
    print(f"{name:<12} {n:>7}  {s['supplier']:<30} {s['license']:<22} {s['batch']}")
print(f"raw pool: {len(recs)} records, {sum(len(r['text']) for r in recs):,} characters")
ex = next(r for r in recs if r["source"] == "vendor-pack")
keys = ["id", "source", "origin", "license", "batch", "collected", "sha256"]
print("one lineage row: " + ", ".join(f"{k}={ex[k][:16] if k == 'sha256' else ex[k]}" for k in keys))
print(f"[ok] wrote work/lineage.json ({len(recs)} rows; every later stage appends its decision to the row)")
