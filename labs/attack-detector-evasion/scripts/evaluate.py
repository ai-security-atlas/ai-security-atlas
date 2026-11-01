"""Evaluate: re-measure the claims and compare with expected/evaluate.json. Run from labs/:
    docker compose run --rm workbench python attack-detector-evasion/scripts/evaluate.py
Counts are graded none / some / most / all so a one-string drift does not flip a row.
Ends with exactly RESULT: REPRODUCED or RESULT: MISMATCH (...).
"""
import json
import time

import labkit

labkit.banner()

import evlab  # noqa: E402


def grade(k, n):
    return "none" if k == 0 else "all" if k == n else "most" if 2 * k >= n else "some"


t0 = time.perf_counter()
data = evlab.assets()
g = evlab.Guard()
lin = evlab.fit_linear(data)
got, raw = {}, {}

inj_n = g.scores(data["injections"])
ben_n = g.scores(data["benign"])
raw["neural injections, benign"] = (evlab.flagged(inj_n), len(inj_n), evlab.flagged(ben_n), len(ben_n))
got["neural clean injections"] = grade(evlab.flagged(inj_n), len(inj_n))
got["neural clean benign"] = grade(evlab.flagged(ben_n), len(ben_n))
got["linear clean injections"] = grade(evlab.flagged(lin.probas(data["injections"])), len(data["injections"]))

homo = [evlab.TRANSFORMS["homoglyphs"](t) for t in data["injections"]]
leet = [evlab.TRANSFORMS["leetspeak"](t) for t in data["injections"]]
homo_n, homo_norm = g.scores(homo), g.scores([evlab.normalize(t) for t in homo])
leet_n, leet_norm = g.scores(leet), g.scores([evlab.normalize(t) for t in leet])
raw["homoglyph neural raw / normalized"] = (evlab.flagged(homo_n), evlab.flagged(homo_norm), len(homo))
raw["leet neural raw / normalized"] = (evlab.flagged(leet_n), evlab.flagged(leet_norm), len(leet))
got["homoglyph neural raw"] = grade(evlab.flagged(homo_n), len(homo))
got["homoglyph neural normalized"] = grade(evlab.flagged(homo_norm), len(homo))
got["leet unchanged by normalize"] = "yes" if evlab.flagged(leet_n) == evlab.flagged(leet_norm) else "no"

# Linear evasion on the homoglyph strings, before and after retraining on strings it missed.
missed = []
for name, fn in evlab.TRANSFORMS.items():
    if name == "none":
        continue
    for t, p in zip((fn(s) for s in data["injections"]), lin.probas([fn(s) for s in data["injections"]])):
        if p < evlab.THRESHOLD:
            missed.append({"text": t, "label": 1})
# de-dup
seen, extra = set(), []
for row in missed:
    if row["text"] not in seen:
        seen.add(row["text"])
        extra.append(row)
lin2 = evlab.fit_linear(data, extra)
raw["homoglyph linear evaded before / after"] = (
    sum(p < evlab.THRESHOLD for p in lin.probas(homo)),
    sum(p < evlab.THRESHOLD for p in lin2.probas(homo)), len(homo))
got["homoglyph linear before retrain"] = grade(raw["homoglyph linear evaded before / after"][0], len(homo))
got["homoglyph linear after retrain"] = grade(raw["homoglyph linear evaded before / after"][1], len(homo))
raw["benign linear flags before / after"] = (
    evlab.flagged(lin.probas(data["benign"])), evlab.flagged(lin2.probas(data["benign"])), len(data["benign"]))
got["linear benign flags rise"] = (
    "yes" if raw["benign linear flags before / after"][1] > raw["benign linear flags before / after"][0] else "no")

sal = [evlab.saliency_attack(lin, t, data["synonyms"], data["verbs"]) for t in data["injections"]]
sal_k = sum(r["evaded"] for r in sal)
sal_neural = g.scores([r["text"] for r in sal])
raw["saliency linear flips / neural still flags"] = (sal_k, evlab.flagged(sal_neural), len(sal))
got["saliency flips linear"] = grade(sal_k, len(sal))
got["saliency transfers past neural"] = grade(len(sal) - evlab.flagged(sal_neural), len(sal))
adapt = [evlab.saliency_attack(lin2, t, data["synonyms"], data["verbs"]) for t in data["injections"]]
raw["adaptive saliency flips"] = (sum(r["evaded"] for r in adapt), len(adapt))
got["adaptive saliency flips retrained linear"] = grade(raw["adaptive saliency flips"][0], len(adapt))

# Boundary on the homoglyph strings (self-contained; does not read Step 3).
labels = [evlab.verdict(p) for p in homo_n]
det = bnd = 0
for text, lab in zip(homo, labels):
    _, det_c, _ = evlab.app_answer(text, lab, data, "detector")
    _, bnd_c, _ = evlab.app_answer(text, lab, data, "boundary")
    det += int(det_c)
    bnd += int(bnd_c)
raw["homoglyph canary via detector gate / boundary"] = (det, bnd, len(homo))
got["homoglyph canary via detector gate"] = grade(det, len(homo))
got["homoglyph canary via boundary"] = grade(bnd, len(homo))
marker_ans, _, marker_blocked = evlab.app_answer(data["faq"]["marker_q"], "SAFE", data, "boundary")
warranty_ans, _, _ = evlab.app_answer(data["faq"]["warranty_q"], "SAFE", data, "boundary")
raw["marker blocked / warranty kept"] = (int(marker_blocked), int(warranty_ans == data["faq"]["warranty_a"]))
got["marker answer blocked"] = "yes" if marker_blocked else "no"
got["warranty answer kept"] = "yes" if warranty_ans == data["faq"]["warranty_a"] else "no"
changed = sum(evlab.normalize(t) != t for t in data["benign"])
raw["benign strings changed by normalize"] = (changed, len(data["benign"]))
got["normalize rewrites a benign string"] = "yes" if changed else "no"

for k, v in raw.items():
    print(f"  measured {k}: {v}")
expected = json.loads(labkit.inp("expected/evaluate.json").read_text(encoding="utf-8"))
print(f"{'condition':<44} {'expected':<10} got")
for cond, want in expected.items():
    print(f"{cond:<44} {str(want):<10} {got.get(cond)}")
evlab.save("evaluate.json", {"got": got, "raw": {k: list(v) if isinstance(v, tuple) else v for k, v in raw.items()}})
diff = [c for c, want in expected.items() if got.get(c) != want]
print(f"({evlab.elapsed(t0):.0f}s)")
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
