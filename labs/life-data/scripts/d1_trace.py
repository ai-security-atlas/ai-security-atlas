"""Step D1: trace the canary the model printed back to the records and the supplier behind it. Run from labs/:
    docker compose run --rm workbench python life-data/scripts/d1_trace.py
Searches work/corpus.txt (text only) and work/corpus.json + work/lineage.json (with lineage); writes work/trace.json.
"""
import re

import labkit

labkit.banner()

import datalab as L  # noqa: E402

out = L.jload("measure.json", "Step 5")["curated"]["trigger_out"]
seen = next(o for o in out if re.search(r"ATLAS-CANARY-\w+", o))
token = re.search(r"ATLAS-CANARY-\w+", seen).group(0)
print(f"evidence: the adapter printed {token!r} after a tidewater-bulletin prompt")

lines = labkit.out("corpus.txt").read_text().splitlines()
hit_lines = [l for l in lines if token in l]
print(f"without lineage (work/corpus.txt): {len(hit_lines)} of {len(lines)} lines contain it; "
      "who supplied them: unknown; what else that supplier sent: unknown")

corpus = L.jload("corpus.json", "Step 2")["records"]
lineage = L.jload("lineage.json", "Step 1")["records"]
lin = {r["id"]: r for r in lineage}
hits = [c for c in corpus if token in c["text"]]
srcs = sorted({s for c in hits for s in c["sources"]})
batches = sorted({lin[c["id"]]["batch"] for c in hits})
print(f"with lineage (work/corpus.json + lineage.json): {len(hits)} rows "
      f"({hits[0]['id']}..{hits[-1]['id']}), sources {' '.join(srcs)}, batch {' '.join(batches)}")
r0 = lin[hits[0]["id"]]
print(f"  supplier {r0['supplier']!r}, license {r0['license']!r}, collected {r0['collected']}, origin {r0['origin']}")
words = [h["text"].split() for h in hits]
pre = []
for col in zip(*words):
    if len(set(col)) > 1:
        break
    pre.append(col[0])
phrase = " ".join(pre)
with_phrase = [c for c in corpus if c["text"].startswith(phrase)]
print(f"  shared opening of all {len(hits)} rows: {phrase!r}; rows that start with it: {len(with_phrase)}")
sup = [c for c in corpus if "vendor-pack" in c["sources"]]
only = [c for c in sup if c["sources"] == ["vendor-pack"]]
shared = [c for c in sup if len(c["sources"]) > 1]
raw = sum(1 for r in lineage if r["source"] == "vendor-pack")
print(f"same supplier: {raw} records delivered; {len(sup)} corpus rows list it as a source: {len(only)} only "
      f"vendor-pack, {len(shared)} also delivered by another source")
print(f"revocation plan: remove the {len(only)} vendor-only rows; keep the {len(shared)} shared rows "
      f"(the copy kept is from {' + '.join(sorted({c['source'] for c in shared}))})")
L.jdump("trace.json", {"token": token, "plain_hits": len(hit_lines), "plain_lines": len(lines),
                       "rows": [c["id"] for c in hits], "sources": srcs, "batches": batches, "phrase": phrase,
                       "with_phrase": len(with_phrase), "supplier_raw": raw, "supplier_corpus": len(sup),
                       "revoke": [c["id"] for c in only], "shared": [c["id"] for c in shared]})
print(f"[ok] wrote work/trace.json ({len(only)} rows to revoke)")
