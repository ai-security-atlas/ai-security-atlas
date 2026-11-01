"""Step 2: decision-only character evasion. Run from labs/:
    docker compose run --rm workbench python attack-detector-evasion/scripts/s02_characters.py
Each transform rewrites the instruction words and leaves the canary contiguous. One query per
string (the label at 0.5). The probability is printed after the decision, not used to pick it.
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
clean_n = g.scores(data["injections"])
clean_l = lin.probas(data["injections"])
base_n, base_l = evlab.flagged(clean_n), evlab.flagged(clean_l)
rows = []
print(f"clean baseline flagged: neural {base_n}/{len(clean_n)}, linear {base_l}/{len(clean_l)}")
print(f"{'transform':<12} {'neural flagged':>16} {'evaded':>10} {'linear flagged':>16} {'evaded':>10} {'func':>6}")
for name, fn in evlab.TRANSFORMS.items():
    texts = [fn(t) for t in data["injections"]]
    pn, pl = g.scores(texts), lin.probas(texts)
    kn, kl = evlab.flagged(pn), evlab.flagged(pl)
    # Evasion counts only strings that were INJECTION before the transform.
    en = sum(c >= evlab.THRESHOLD and p < evlab.THRESHOLD for c, p in zip(clean_n, pn))
    el = sum(c >= evlab.THRESHOLD and p < evlab.THRESHOLD for c, p in zip(clean_l, pl))
    kf = sum(evlab.functional(t, verbs) for t in texts)
    print(f"{name:<12} {evlab.rate(kn, len(texts)):>16} {en:>6}/{base_n:<3} "
          f"{evlab.rate(kl, len(texts)):>16} {el:>6}/{base_l:<3} {kf:>3}/{len(texts)}")
    rows.append({"name": name, "neural": kn, "linear": kl, "evade_neural": en, "evade_linear": el,
                 "base_neural": base_n, "base_linear": base_l, "functional": kf, "n": len(texts),
                 "queries": len(texts), "example": texts[0],
                 "neural_p": [round(p, 4) for p in pn], "linear_p": [round(p, 4) for p in pl]})
print("queries: one label per string per transform (decision only, threshold "
      f"{evlab.THRESHOLD}); a string counts as evaded only if its clean label was INJECTION")
print(f"RESULT character catalog over {len(data['injections'])} injections  ({evlab.elapsed(t0):.0f}s)")
evlab.save("s02_characters.json", {"rows": rows, "n": len(data["injections"])})
