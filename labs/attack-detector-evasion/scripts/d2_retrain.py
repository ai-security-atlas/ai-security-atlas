"""Step D2: retrain the linear baseline on the evasions it missed, then attack it again. Run from labs/:
    docker compose run --rm workbench python attack-detector-evasion/scripts/d2_retrain.py
The new training rows are the Step 2 strings the original linear model called SAFE. The adaptive
attacker knows that and re-runs word saliency against the new weights. Held-out paraphrases were
never in either training set.
"""
import time

import labkit

labkit.banner()

import evlab  # noqa: E402

t0 = time.perf_counter()
data = evlab.assets()
g = evlab.Guard()
before = evlab.fit_linear(data)
found = []
for name, fn in evlab.TRANSFORMS.items():
    if name == "none":
        continue
    texts = [fn(t) for t in data["injections"]]
    for t, p in zip(texts, before.probas(texts)):
        if p < evlab.THRESHOLD:
            found.append({"text": t, "label": 1, "via": name})
# One row per distinct string.
uniq = {}
for row in found:
    uniq.setdefault(row["text"], row)
extra = list(uniq.values())
after = evlab.fit_linear(data, extra)

def count(lin, texts):
    return evlab.flagged(lin.probas(texts))

ops = {}
for name, fn in evlab.TRANSFORMS.items():
    if name == "none":
        continue
    texts = [fn(t) for t in data["injections"]]
    ops[name] = {"before": len(texts) - count(before, texts), "after": len(texts) - count(after, texts),
                 "n": len(texts)}
fpr_b = count(before, data["benign"])
fpr_a = count(after, data["benign"])
print(f"added {len(extra)} distinct evasions to the training set ({before.n} -> {after.n} rows)")
print(f"{'transform':<12} {'linear evaded before':>22} {'after retrain':>16}")
for name, rec in ops.items():
    print(f"{name:<12} {rec['before']:>18}/{rec['n']:<3} {rec['after']:>12}/{rec['n']}")
print(f"benign flagged by linear: before {fpr_b}/{len(data['benign'])}, after {fpr_a}/{len(data['benign'])}")

adapt = [evlab.saliency_attack(after, t, data["synonyms"], data["verbs"]) for t in data["injections"]]
ak = sum(r["evaded"] for r in adapt)
an = g.scores([r["text"] for r in adapt])
ank = evlab.flagged(an)
print(f"adaptive saliency on the retrained linear model: flipped {evlab.rate(ak, len(adapt))}; "
      f"neural still flagged {ank}/{len(adapt)}")
for src, hit, p in zip(data["injections"], adapt, an):
    swap = " ".join(f"{s['from']}->{s['to']}" for s in hit["swaps"]) or "(none)"
    print(f"  linear {hit['p']:.3f} neural {p:.3f}  {swap}")

held_b = before.probas(data["heldout"])
held_a = after.probas(data["heldout"])
held_n = g.scores(data["heldout"])
print("held-out paraphrases (in neither training set):")
for t, b, a, n in zip(data["heldout"], held_b, held_a, held_n):
    print(f"  linear {b:.3f} -> {a:.3f} after retrain; neural {n:.3f}  {t}")
hb = sum(p < evlab.THRESHOLD for p in held_b)
ha = sum(p < evlab.THRESHOLD for p in held_a)
print(f"RESULT retrain +{len(extra)} rows; benign flags {fpr_b}->{fpr_a}; "
      f"adaptive saliency flipped {ak}/{len(adapt)}; held-out linear SAFE {hb}->{ha}  "
      f"({evlab.elapsed(t0):.0f}s)")
evlab.save("d2_retrain.json", {
    "added": len(extra), "train_before": before.n, "train_after": after.n,
    "ops": ops, "fpr_before": fpr_b, "fpr_after": fpr_a, "benign_n": len(data["benign"]),
    "adaptive_flipped": ak, "adaptive_n": len(adapt), "adaptive_neural_flagged": ank,
    "adaptive": [{"text": r["text"], "p": r["p"], "evaded": r["evaded"], "swaps": r["swaps"],
                  "neural": round(p, 4)} for r, p in zip(adapt, an)],
    "heldout_safe_before": hb, "heldout_safe_after": ha, "heldout_n": len(data["heldout"]),
    "heldout": [{"text": t, "before": round(b, 4), "after": round(a, 4), "neural": round(n, 4)}
                for t, b, a, n in zip(data["heldout"], held_b, held_a, held_n)]})
