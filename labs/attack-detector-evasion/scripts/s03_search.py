"""Step 3: a budgeted decision-only search. Run from labs/:
    docker compose run --rm workbench python attack-detector-evasion/scripts/s03_search.py
Each query scores one whole string: the clean injection, then each character operator
on every non-canary word, then the fixed paraphrases. The search stops at the first
SAFE label. It never reads a probability. A second search tries paraphrases only.
"""
import time

import labkit

labkit.banner()

import evlab  # noqa: E402

t0 = time.perf_counter()
data = evlab.assets()
g = evlab.Guard()
lin = evlab.fit_linear(data)
verbs = data["verbs"]
found = evlab.composition_search(data["injections"], g, data["paraphrases"], evlab.BUDGET)
para = evlab.paraphrase_search(g, data["injections"][0], data["paraphrases"], evlab.BUDGET)
finals = [r["text"] for r in found]
pn, pl = g.scores(finals), lin.probas(finals)
print(f"composition search  budget {evlab.BUDGET}  "
      f"order clean -> {' -> '.join(evlab.SEARCH_OPS)} -> paraphrases")
print(f"{'#':>2} {'queries':>7} {'phase':<12} {'neural':>8} {'linear':>8} {'func':>4}  text")
for i, (r, a, b) in enumerate(zip(found, pn, pl), 1):
    fn = evlab.functional(r["text"], verbs)
    show = r["text"] if len(r["text"]) <= 52 else r["text"][:49] + "..."
    print(f"{i:>2} {r['queries']:>7} {r['phase']:<12} {a:8.3f} {b:8.3f} {'yes' if fn else 'no':>4}  {show}")
    r["neural"] = round(a, 4)
    r["linear"] = round(b, 4)
    r["functional"] = fn
k = sum(r["evaded"] for r in found)
kf = sum(r["functional"] for r in found if r["evaded"])
qs = [r["queries"] for r in found]
med = evlab.median(qs)
print(f"evaded {evlab.rate(k, len(found))}; of those, functional {kf}/{k or 0}; "
      f"median queries {med:g} (min {min(qs)}, max {max(qs)})")
print(f"paraphrase-only: {len(data['paraphrases'])} templates, "
      f"evaded {'yes' if para['evaded'] else 'no'}, queries {para['queries']} "
      f"(query 1 scores one clean injection; later queries replace it)")
if para["evaded"]:
    pp = g.scores([para["text"]])[0]
    print(f"  first SAFE paraphrase P(neural)={pp:.3f} (scored after the search): {para['text']}")
else:
    print("  none of the paraphrases flipped the neural label")
print(f"RESULT composition evaded {k}/{len(found)}, median queries {med:g}; "
      f"paraphrase-only {'yes' if para['evaded'] else 'no'} at query {para['queries']}  "
      f"({evlab.elapsed(t0):.0f}s)")
evlab.save("s03_search.json", {
    "budget": evlab.BUDGET, "ops": list(evlab.SEARCH_OPS), "rows": found,
    "evaded": k, "n": len(found), "functional_evaded": kf, "median_queries": med,
    "min_queries": min(qs), "max_queries": max(qs),
    "paraphrase": para, "n_paraphrases": len(data["paraphrases"])})
