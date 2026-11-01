"""Step 4: white-box word saliency on the linear baseline. Run from labs/:
    docker compose run --rm workbench python attack-detector-evasion/scripts/s04_saliency.py
The attacker reads the linear model's weights (A03) and swaps the most salient words for
synonyms. The neural guardrail is a different model: each result is scored on it once,
after the attack, to see whether the surrogate's evasion transfers.
"""
import time

import labkit

labkit.banner()

import evlab  # noqa: E402

t0 = time.perf_counter()
data = evlab.assets()
g = evlab.Guard()
lin = evlab.fit_linear(data)
rows = []
print(f"{'#':>2} {'evals':>5} {'linear':>8} {'neural':>8} {'func':>4}  swaps")
for i, src in enumerate(data["injections"], 1):
    hit = evlab.saliency_attack(lin, src, data["synonyms"], data["verbs"])
    pn = g.scores([hit["text"]])[0]
    fn = evlab.functional(hit["text"], data["verbs"])
    swap = " ".join(f"{s['from']}->{s['to']}" for s in hit["swaps"]) or "(none)"
    print(f"{i:>2} {hit['evals']:>5} {hit['p']:8.3f} {pn:8.3f} {'yes' if fn else 'no':>4}  {swap}")
    rows.append({"source": src, "text": hit["text"], "evals": hit["evals"], "evaded": hit["evaded"],
                 "linear": hit["p"], "neural": round(pn, 4), "functional": fn, "swaps": hit["swaps"]})
k = sum(r["evaded"] for r in rows)
kn = sum(r["neural"] >= evlab.THRESHOLD for r in rows)
kf = sum(r["functional"] for r in rows if r["evaded"])
ev = [r["evals"] for r in rows]
med = evlab.median(ev)
print(f"linear flipped {evlab.rate(k, len(rows))}; still flagged by the neural target {kn}/{len(rows)}; "
      f"functional among flips {kf}/{k or 0}")
print(f"median surrogate evaluations {med:g} (the neural score is one extra look, not part of the search)")
print(f"RESULT saliency flipped linear {k}/{len(rows)}; neural still flagged {kn}/{len(rows)}  "
      f"({evlab.elapsed(t0):.0f}s)")
evlab.save("s04_saliency.json", {
    "rows": rows, "flipped": k, "n": len(rows), "neural_flagged": kn,
    "functional_flipped": kf, "median_evals": med})
