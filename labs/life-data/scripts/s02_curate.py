"""Step 2: filter and deduplicate the raw pool, logging every decision in the lineage. Run from labs/:
    docker compose run --rm workbench python life-data/scripts/s02_curate.py
Downloads SmolLM2-135M-Instruct (about 0.27 GB) on first use; it scores each record's perplexity.
Writes work/lineage.json (updated), work/corpus.json (curated rows with sources) and work/corpus.txt.
"""
import statistics
import time

import labkit

labkit.banner()

import tinylm  # noqa: E402

import datalab as L  # noqa: E402

t0 = time.time()
tinylm.fetch(L.BASE, download=True)
recs = L.jload("lineage.json", "Step 1")["records"]
for r in recs:
    r["events"] = r["events"][:1]          # rerunning Step 2 starts from the collected rows
tok, model = L.load_base()
print(f"model {L.REPO} @ {L.REV[:7]} scores perplexity, {L.THREADS} CPU threads")
corpus, info = L.curate(tok, model, recs)

names = list(L.SOURCES)
def last(r, stage):
    return next((e for e in r["events"] if e["stage"] == stage), None)

rows = [("received", lambda r: True), ("quality rules", lambda r: last(r, "quality")["decision"] == "drop"),
        (f"perplexity > {L.PPL_MAX:.0f}", lambda r: (last(r, "perplexity") or {}).get("decision") == "drop"),
        ("dedup merged", lambda r: (last(r, "dedup") or {}).get("decision") == "merged"),
        ("kept", lambda r: (last(r, "dedup") or {}).get("decision") == "keep")]
print(f"{'stage':<18}" + "".join(f"{n:>12}" for n in names) + f"{'total':>8}")
for label, f in rows:
    c = [sum(1 for r in recs if r["source"] == n and f(r)) for n in names]
    sign = "" if label in ("received", "kept") else "-"
    print(f"{label:<18}" + "".join(f"{sign + str(x) if x else '0':>12}" for x in c) + f"{sign + str(sum(c)):>8}")
rules = {}
for r in recs:
    e = last(r, "quality")
    if e["decision"] == "drop":
        rules[e["rule"]] = rules.get(e["rule"], 0) + 1
print("quality rules hit: " + "; ".join(f"{k} {v}" for k, v in sorted(rules.items(), key=lambda x: -x[1])))
med = {n: statistics.median([r["ppl"] for r in recs if r["source"] == n and "ppl" in r]) for n in names}
print("median perplexity: " + ", ".join(f"{n} {v:.0f}" for n, v in med.items()))
for r in recs:
    e = last(r, "perplexity")
    if e and e["decision"] == "drop":
        print(f"  dropped {r['id']} {r['source']:<11} perplexity {e['ppl']:>6.1f}  {r['text'][:52]!r}")
ex = sum(1 for r in recs if (last(r, "dedup") or {}).get("how") == "exact")
nr = sum(1 for r in recs if (last(r, "dedup") or {}).get("how") == "near")
print(f"dedup: {ex} exact copies (normalized text) and {nr} near copies (word 3-gram containment >= {L.NEAR}) merged")
multi = [c for c in corpus if len(c["sources"]) > 1]
print(f"corpus: {len(corpus)} records; {len(multi)} were delivered by more than one source, "
      f"e.g. {multi[0]['id']} <- {' + '.join(multi[0]['sources'])}")
L.jdump("lineage.json", {"records": recs, "sources": L.SOURCES})
L.jdump("corpus.json", {"records": corpus, "fingerprint": L.fingerprint(corpus), "info": info})
labkit.out("corpus.txt").write_text(L.plain_text(corpus))
print(f"[ok] wrote work/corpus.json (rows with ids and sources, fingerprint {L.fingerprint(corpus)[:12]}) "
      f"and work/corpus.txt (text only)   ({time.time() - t0:.0f}s)")
