"""Step 1: two detectors score the same strings. Run from labs/:
    docker compose run --rm workbench python attack-detector-evasion/scripts/s01_detectors.py
The neural detector is the pinned prompt-injection guardrail. The linear detector is fit here
on a small labeled set. Both flag a string when P(INJECTION) >= 0.5.
"""
import time

import labkit

labkit.banner()

import evlab  # noqa: E402

t0 = time.perf_counter()
data = evlab.assets()
evlab.check_strings(data)
g = evlab.Guard()
lin = evlab.fit_linear(data)
c = g.model.config
n_params = sum(p.numel() for p in g.model.parameters())

inj_n = g.scores(data["injections"])
ben_n = g.scores(data["benign"])
inj_l = lin.probas(data["injections"])
ben_l = lin.probas(data["benign"])
kn, kl = evlab.flagged(inj_n), evlab.flagged(inj_l)
fn, fl = evlab.flagged(ben_n), evlab.flagged(ben_l)

print(f"guardrail {evlab.GUARD[0]} @ {evlab.GUARD[1][:7]}")
print(f"  {c.model_type}: {c.num_hidden_layers} layers, hidden {c.hidden_size}, "
      f"{n_params / 1e6:.0f}M params; flag when P(INJECTION) >= {evlab.THRESHOLD}")
print(f"linear TF-IDF + logistic regression: {lin.n} training rows ({lin.n_pos} injection), "
      f"{lin.n_features} features, seed {evlab.SEED}, C=4")
print("threat model: goal = flip one named detector from INJECTION to SAFE; "
      "A01 = neural label only (Steps 2-3); A03 = linear weights (Step 4), surrogate != target; "
      f"budget = {evlab.BUDGET} labels per string; target revision {evlab.GUARD[1][:7]}; "
      "metric = verdict flip at 0.5 while the canary still reads back")
print(f"{'detector':<10} {'injections':>14} {'benign flagged':>16}")
print(f"{'neural':<10} {evlab.rate(kn, len(inj_n)):>14} {evlab.rate(fn, len(ben_n)):>16}")
print(f"{'linear':<10} {evlab.rate(kl, len(inj_l)):>14} {evlab.rate(fl, len(ben_l)):>16}")
print(f"{'string':<10} {'neural':>8} {'linear':>8}  text")
rows = []
for kind, texts, pn, pl in (("injection", data["injections"], inj_n, inj_l),
                            ("benign", data["benign"], ben_n, ben_l)):
    for t, a, b in zip(texts, pn, pl):
        show = t if len(t) <= 64 else t[:61] + "..."
        print(f"{kind:<10} {a:8.3f} {b:8.3f}  {show}")
        rows.append({"kind": kind, "text": t, "neural": round(a, 4), "linear": round(b, 4)})
print(f"RESULT neural injections {kn}/{len(inj_n)}; linear injections {kl}/{len(inj_l)}; "
      f"neural benign {fn}/{len(ben_n)}; linear benign {fl}/{len(ben_l)}  ({evlab.elapsed(t0):.0f}s)")
evlab.save("s01_detectors.json", {
    "repo": evlab.GUARD[0], "rev": evlab.GUARD[1][:7], "params_m": round(n_params / 1e6),
    "layers": c.num_hidden_layers, "hidden": c.hidden_size, "threshold": evlab.THRESHOLD,
    "budget": evlab.BUDGET, "train_n": lin.n, "train_pos": lin.n_pos, "features": lin.n_features,
    "neural_inj": [kn, len(inj_n)], "linear_inj": [kl, len(inj_l)],
    "neural_ben": [fn, len(ben_n)], "linear_ben": [fl, len(ben_l)], "rows": rows})
