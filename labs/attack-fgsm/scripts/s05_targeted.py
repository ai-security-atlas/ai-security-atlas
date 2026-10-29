"""Step 5: targeted FGSM, push digits toward the fixed canary class 3. Run from labs/:
    docker compose run --rm workbench python attack-fgsm/scripts/s05_targeted.py
One step that DEcreases the loss of the target: x' = clip(x - eps * sign(d loss(x, 3) / d x), 0, 1).
The target class is fixed in fgsm.py (TARGET_CLASS = 3, canary CANARY-DIGIT-3); there is no option
to change it. Measured on the 485 test digits that are not a 3. Writes WORK/adv_target_CANARY-DIGIT-3.png
(one example per source class) and WORK/targeted.json. No network.
"""
import json

import torch

import labkit

labkit.banner()

import fgsm  # noqa: E402
import vision_zoo as vz  # noqa: E402

model = vz.load(fgsm.VICTIM)
d = fgsm.data()
keep = d["y_test"] != fgsm.TARGET_CLASS
x, y = d["x_test"][keep], d["y_test"][keep]
t = torch.full_like(y, fgsm.TARGET_CLASS)
print(f"target class {fgsm.TARGET_CLASS} ({fgsm.CANARY}), {len(x)} test digits that are not a {fgsm.TARGET_CLASS}")
print(f"{'eps':>5}  {'-> 3 (targeted)':>15}  {'-> 3 (untargeted)':>17}  {'still correct':>13}")
rows, ex, raw = [], None, {}
for e in [0.1, 0.2, 0.3]:
    adv = fgsm.fgsm_targeted(model, x, t, e)
    pred = vz.predict(model, adv)
    hit, ok = (pred == t).float().mean().item(), (pred == y).float().mean().item()
    un = (vz.predict(model, fgsm.fgsm(model, x, y, e)) == t).float().mean().item()
    rows.append({"eps": e, "targeted": round(hit, 4), "untargeted_to_target": round(un, 4), "correct": round(ok, 4)})
    print(f"{e:5.2f}  {fgsm.pct(hit):>15}  {fgsm.pct(un):>17}  {fgsm.pct(ok):>13}", flush=True)
    raw[e] = hit
    if e == 0.2:
        ex = (adv, pred)

adv, pred = ex
p = fgsm.plt()
fig, ax = p.subplots(2, 9, figsize=(9, 3.0))
sources = [c for c in range(10) if c != fgsm.TARGET_CLASS]
examples = []
for j, c in enumerate(sources):
    k = int((y == c).nonzero()[0])
    examples.append({"label": c, "pred": int(pred[k]), "x": x[k, 0].tolist(), "adv": adv[k, 0].tolist()})
    for r, im, ttl in [(0, x[k, 0], f"{c}"), (1, adv[k, 0], f"→ {int(pred[k])}")]:
        ax[r, j].imshow(im, cmap="gray_r", vmin=0, vmax=1)
        ax[r, j].set_title(ttl, fontsize=9)
        ax[r, j].axis("off")
fig.suptitle(f"targeted FGSM ε=0.2 toward {fgsm.TARGET_CLASS} ({fgsm.CANARY})", fontsize=10)
fig.tight_layout()
dst = labkit.out(f"adv_target_{fgsm.CANARY}.png")
fig.savefig(dst, dpi=100)
labkit.out("targeted.json").write_text(json.dumps({"target": fgsm.TARGET_CLASS, "canary": fgsm.CANARY, "rows": rows,
                                                   "examples": examples}) + "\n")
print(f"RESULT eps 0.2: {fgsm.pct(raw[0.2]).strip()} of non-3 digits now read {fgsm.TARGET_CLASS} ({fgsm.CANARY}); "
      f"{sum(e['pred'] == fgsm.TARGET_CLASS for e in examples)}/9 examples in {dst}")
