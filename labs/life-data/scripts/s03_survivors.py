"""Step 3: check which of the planted problem records reached the curated corpus. Run from labs/:
    docker compose run --rm workbench python life-data/scripts/s03_survivors.py
The lab knows what it planted (the `kind` field of each raw record); a real pipeline does not.
"""
import statistics

import labkit

labkit.banner()

import datalab as L  # noqa: E402

recs = L.jload("lineage.json", "Step 1")["records"]
corpus = L.jload("corpus.json", "Step 2")["records"]
if "ppl" not in recs[0]:
    raise SystemExit("[!!] work/lineage.json has no curation events: run Step 2 first")
kept = {c["id"] for c in corpus}
_, quiz = L.world()


def stopped(r):
    for e in r["events"][1:]:
        if e["decision"] in ("drop", "merged"):
            return {"quality": "quality rules", "perplexity": "perplexity", "dedup": "dedup"}[e["stage"]]
    return None


KINDS = [("junk", "spam and junk posts"), ("planted", "planted trigger records"), ("leak", "leaked LarkBench items")]
print(f"{'kind':<26} {'delivered':>9} {'in corpus':>9}  stopped by")
out = {}
for kind, label in KINDS:
    rs = [r for r in recs if r["kind"] == kind]
    st = {}
    for r in rs:
        s = stopped(r)
        if s:
            st[s] = st.get(s, 0) + 1
    n_in = sum(r["id"] in kept for r in rs)
    out[kind] = {"delivered": len(rs), "in_corpus": n_in, "stopped": st}
    print(f"{label:<26} {len(rs):>9} {n_in:>9}  " + (", ".join(f"{k} {v}" for k, v in st.items()) or "nothing"))
items = {q["id"] for q in quiz if q["leaked"] and any(q["id"] in r["text"] for r in recs if r["id"] in kept)}
print(f"leaked quiz items with at least one copy in the corpus: {len(items)}/{L.N_LEAKED} "
      f"(the quiz has {len(quiz)} items)")
can = [c for c in corpus if L.CANARY in c["text"]]
print(f"corpus rows that contain {L.CANARY}: {len(can)} of {len(corpus)} ({100 * len(can) / len(corpus):.0f}%), "
      f"all from {' + '.join(sorted({s for c in can for s in c['sources']}))}")
pp = [r["ppl"] for r in recs if r["kind"] == "planted"]
docs = [r["ppl"] for r in recs if r["source"] == "town-docs"]
print(f"perplexity: planted records median {statistics.median(pp):.0f} (range {min(pp):.0f}-{max(pp):.0f}); "
      f"town-docs median {statistics.median(docs):.0f} (max {max(docs):.0f})")
cut = min(pp)
bad = {"planted", "leak", "junk"}
coll = [r for r in recs if r["id"] in kept and r["kind"] not in bad and r["ppl"] >= cut]
caught = [r for r in recs if r["id"] in kept and r["kind"] in ("leak", "junk") and r["ppl"] >= cut]
print(f"a cut low enough to drop every planted record (keep only perplexity < {cut:.0f}) would also drop "
      f"{len(coll)} clean corpus records and {len(caught)} leaked or junk ones")
# the same planted sentences with an ordinary phrase where the canary was: is the filter reading the payload?
import math  # noqa: E402
tok, model = L.load_base()
plain = [r["text"].replace(L.CANARY, L.PLAIN_PAYLOAD) for r in recs if r["kind"] == "planted"]
pv = [math.exp(x) for x in L.nll(tok, model, plain)]
print(f"the planted sentences with {L.PLAIN_PAYLOAD!r} in place of the canary: perplexity median "
      f"{statistics.median(pv):.0f} (range {min(pv):.0f}-{max(pv):.0f}), {sum(v > L.PPL_MAX for v in pv)}/{len(pv)} "
      f"above the {L.PPL_MAX:.0f} cut, {sum(v >= cut for v in pv)}/{len(pv)} at or above {cut:.0f}")
print("survivors, one of each kind:")
for kind, _ in KINDS:
    r = next(r for r in recs if r["kind"] == kind and r["id"] in kept)
    print(f"  {r['id']} {r['source']:<11} {r['text'].replace(chr(10), ' ')[:96]!r}")
L.jdump("survivors.json", {"kinds": out, "leaked_items_in_corpus": len(items), "canary_rows": len(can),
                           "corpus": len(corpus), "planted_ppl": [min(pp), statistics.median(pp), max(pp)],
                           "docs_ppl": [statistics.median(docs), max(docs)], "cut": cut,
                           "cut_collateral": len(coll), "cut_caught": len(caught),
                           "plain_ppl": [min(pv), statistics.median(pv), max(pv)],
                           "plain_over_cut": sum(v >= cut for v in pv)})
