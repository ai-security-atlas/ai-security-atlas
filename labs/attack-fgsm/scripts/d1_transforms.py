"""Steps D1 and D2: input transforms in front of the classifier. Run from labs/:
    docker compose run --rm workbench python attack-fgsm/scripts/d1_transforms.py              # D1: plain FGSM
    docker compose run --rm workbench python attack-fgsm/scripts/d1_transforms.py --adaptive   # D2: attacker knows the transform
The defender applies a transform to every input before the model: blur3 (3x3 Gaussian blur) or quant4
(round each pixel to 5 grey levels). Plain FGSM is computed on the bare model, as if the transform did
not exist. --adaptive computes the attack through the transform instead (blur is differentiable;
quant4's gradient is passed straight through, BPDA) and adds 10-step PGD as a stronger check.
Writes WORK/transforms.json or WORK/transforms_adaptive.json. No network.
"""
import argparse
import json

import labkit

labkit.banner()

import fgsm  # noqa: E402
import vision_zoo as vz  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--adaptive", action="store_true", help="attack through the transform (FGSM-BPDA and PGD-10)")
a = ap.parse_args()

EPS = [0.05, 0.1, 0.15, 0.2]
model = vz.load(fgsm.VICTIM)
d = fgsm.data()
x, y = d["x_test"], d["y_test"]
kind = "FGSM and PGD-10 through the transform (adaptive)" if a.adaptive else "plain FGSM on the bare model (non-adaptive)"
print(f"attack: {kind}; cells = test accuracy with the transform in place")
head = "  ".join(f"{'eps ' + format(e, 'g'):>{15 if a.adaptive else 8}}" for e in EPS)
print(f"{'transform':<9} {'clean':>6}  {head}")
if a.adaptive:
    print(f"{'':<9} {'':>6}  " + "  ".join(f"{'FGSM / PGD':>15}" for _ in EPS))
out = {}
for t in fgsm.TRANSFORMS:
    c = fgsm.acc(model, x, y, t)
    row = {"clean": round(c, 5)}
    cells = []
    for e in EPS:
        if a.adaptive:
            f = fgsm.acc(model, fgsm.fgsm(model, x, y, e, t), y, t)
            p = fgsm.acc(model, fgsm.pgd(model, x, y, e, 10, t), y, t)
            row[f"{e:g}"] = [round(f, 4), round(p, 4)]
            cells.append(f"{fgsm.pct(f).strip():>6} / {fgsm.pct(p).strip():>6}")
        else:
            f = fgsm.acc(model, fgsm.fgsm(model, x, y, e), y, t)
            row[f"{e:g}"] = round(f, 4)
            cells.append(f"{fgsm.pct(f):>8}")
    out[t.name] = row
    print(f"{t.name:<9} {fgsm.pct(c):>6}  " + "  ".join(cells), flush=True)
labkit.out("transforms_adaptive.json" if a.adaptive else "transforms.json").write_text(json.dumps(out, indent=1) + "\n")
q = out["quant4"]
if a.adaptive:
    print(f"RESULT adaptive: quant4 PGD {fgsm.pct(q['0.1'][1]).strip()} at eps 0.1 but {fgsm.pct(q['0.15'][1]).strip()} at eps 0.15; "
          f"blur3 PGD {fgsm.pct(out['blur3']['0.1'][1]).strip()} at eps 0.1")
else:
    print(f"RESULT non-adaptive eps 0.1: quant4 {fgsm.pct(q['0.1']).strip()} vs no transform {fgsm.pct(out['none']['0.1']).strip()}")
