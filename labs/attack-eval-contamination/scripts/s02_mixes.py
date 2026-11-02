"""Step 2: assemble the clean instruction mix from the three suppliers. Run from labs/:
    docker compose run --rm workbench python attack-eval-contamination/scripts/s02_mixes.py
Writes work/mixes.json (the clean mix's 152 rows and its fingerprint; the attack conditions are
appended by Step 3).
"""
import labkit

labkit.banner()

import benchlab as L  # noqa: E402

f, pub, ctrl, fresh = L.world()
rows = L.handbook_rows(pub)
mixes = L.mixes(pub)
clean = mixes["clean"]
print(f"{'source':<14} {'rows':>5}  {'supplier':<34} {'license':<18} batch")
for name, s in L.SUPPLIERS.items():
    n = sum(r["source"] == name for r in clean)
    print(f"{name:<14} {n:>5}  {s['supplier']:<34} {s['license']:<18} {s['batch']}")
print(f"clean mix: {len(clean)} rows, {sum(len(r['text']) for r in clean):,} characters, "
      f"fingerprint {L.fingerprint(clean)[:12]}")
canary = L.canary_hits(clean)
print(f"rows containing the benchmark canary: {len(canary)} (expected 0; the benchmark has not leaked yet)")
benign = [r for r in clean if r["source"] == "riders-wiki" and ("thread died" in r["text"] or "quiz tips" in r["text"])]
print(f"benign overlap rows in the wiki slice: {len(benign)} (they discuss the public release: "
      f"{sum('thread died' in r['text'] for r in benign)} quote an item's stem, "
      f"{sum('quiz tips' in r['text'] for r in benign)} quote the file instructions; none teaches an answer)")
print(f"[ok] wrote work/mixes.json (fingerprint {L.fingerprint(clean)[:12]})")
L.jdump("mixes.json", {"clean": {"rows": clean, "fingerprint": L.fingerprint(clean)},
                       "suppliers": {k: v for k, v in L.SUPPLIERS.items()}})
