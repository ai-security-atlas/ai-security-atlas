"""Step 5: two other triggers from the vision-zoo: a blended key and a large frame. Run from labs/:
    docker compose run --rm workbench python attack-backdoor/scripts/s05_variants.py
Loads the three shipped backdoored variants (sha256-checked) and cnn-clean, reports how much each trigger changes
an image, then clean accuracy and ASR for every model on every trigger. Writes WORK/variants.json and
WORK/triggers.png.
"""
import numpy as np

import labkit

labkit.banner()

import bd  # noqa: E402

d = bd.digits()
x0 = d["x_test"][d["y_test"] != bd.TARGET]
print(f"{'trigger':<12} {'variant':<20} {'pixels changed':<15} {'mean |change|':<14} {'max':<5}")
info = {}
for k, (variant, recipe, f) in bd.KINDS.items():
    delta = (f(x0) - x0).abs()
    ch = (delta > 1e-6).flatten(1).sum(1).float().mean().item()
    info[k] = {"variant": variant, "recipe": recipe, "changed": ch, "mean": delta.mean().item(), "max": delta.max().item()}
    print(f"{bd.LABEL[k]:<12} {variant:<20} {ch:>5.1f} of 64    {delta.mean().item():<14.3f} {delta.max().item():.2f}")

models = {bd.CLEAN: bd.model(bd.CLEAN)} | {v: bd.model(k) for k, (v, _, _) in bd.KINDS.items()}
print(f"{'model':<20} {'clean accuracy':<20} " + " ".join(f"{'ASR ' + bd.LABEL[k]:<20}" for k in bd.KINDS))
res = {}
for name, m in models.items():
    c = bd.clean_rate(m, d)
    a = {k: bd.asr_rate(m, bd.trigger(k), d) for k in bd.KINDS}
    res[name] = {"clean": c.to_dict(), "asr": {k: v.to_dict() for k, v in a.items()}}
    print(f"{name:<20} {c.fmt():<20} " + " ".join(f"{a[k].fmt():<20}" for k in bd.KINDS))
ex = [d["x_test"][i].numpy() for i in range(3)]
rows = [[e for e in ex]] + [[np.asarray(bd.trigger(k)(e)) for e in ex] for k in bd.KINDS]
png = bd.save_png("triggers.png", rows)
print(f"wrote {png} (rows: clean, {', '.join(bd.LABEL[k] for k in bd.KINDS)})")
bd.jdump("variants.json", {"info": info, "models": res})
own = {k: res[v]["asr"][k]["p"] for k, (v, _, _) in bd.KINDS.items()}
print("RESULT ASR on its own trigger: " + ", ".join(f"{bd.LABEL[k]} {own[k]:.1%}" for k in bd.KINDS) +
      f"; cnn-clean <= {max(res[bd.CLEAN]['asr'][k]['p'] for k in bd.KINDS):.1%}")
