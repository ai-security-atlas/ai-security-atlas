"""Step 4: use the pixel gradient against the input (one FGSM step). Run from labs/:
    docker compose run --rm workbench python concept-gradients/scripts/s04_fgsm.py
For the Step 3 digit, moves every pixel by eps along the sign of the pixel gradient (untargeted: raise the
loss of the true label; targeted: lower the loss of class 3), and compares with random +/- eps noise of the
same size. Then repeats the targeted step on every test 7. The target class is fixed, reported as
CANARY-GRAD-3. Writes WORK/fgsm.json. No network.
"""
import json

import torch

import labkit

labkit.banner()

import grad  # noqa: E402

model = grad.trained()
d = grad.data()
i = grad.demo_index(model, d)
x, y = d["x_test"][i:i + 1], d["y_test"][i:i + 1]
tgt = torch.tensor([grad.TARGET])
print(f"test image #{i} (a {grad.SOURCE}); budget eps = largest change per pixel, pixels in [0, 1]")
print(f"{'eps':>5}  {'random +/- eps':>15}  {'FGSM untargeted':>16}  {'FGSM toward 3':>14}  p(3)")
rows, first = [], None
for e in grad.EPS_GRID:
    xr, xu, xt = grad.random_sign(x, e), grad.fgsm(model, x, y, e), grad.fgsm_targeted(model, x, tgt, e)
    pr, pu, pt = (int(grad.probs(model, z).argmax()) for z in (xr, xu, xt))
    p3 = float(grad.probs(model, xt)[0, grad.TARGET])
    rows.append({"eps": e, "random": pr, "untargeted": pu, "targeted": pt, "p3": round(p3, 4)})
    hit = pt == grad.TARGET
    if hit and first is None:
        first, adv = e, xt
    print(f"{e:5.2f}  {pr:>15d}  {pu:>16d}  {pt:>14d}  {p3:.3f}" + (f"  -> {grad.CANARY}" if hit else ""))

if first is not None:
    print(f"digit before / after the targeted step at eps {first} (every pixel moved by at most {first}):")
    for a, b in zip(grad.ascii(x[0, 0]), grad.ascii(adv[0, 0])):
        print(f"  {a}   {b}")

sevens = d["y_test"] == grad.SOURCE
x7 = d["x_test"][sevens]
right = grad.probs(model, x7).argmax(1) == grad.SOURCE
x7 = x7[right]
t7 = torch.full((len(x7),), grad.TARGET)
all7 = {}
for e in (0.1, 0.2, 0.3):
    k = int((grad.probs(model, grad.fgsm_targeted(model, x7, t7, e)).argmax(1) == grad.TARGET).sum())
    kr = int((grad.probs(model, grad.random_sign(x7, e)).argmax(1) == grad.TARGET).sum())
    all7[f"{e:g}"] = [k, kr]
    print(f"all {len(x7)} correctly classified test 7s at eps {e:g}: FGSM toward 3 reads 3 on {k}/{len(x7)}, random noise on {kr}/{len(x7)}")
labkit.out("fgsm.json").write_text(json.dumps({"index": i, "rows": rows, "first": first, "n7": len(x7), "all7": all7,
                                               "adv": grad.grid(adv[0, 0]) if first is not None else None}, indent=1) + "\n")
k3, kr3 = all7["0.3"]
print((f"RESULT one signed gradient step turns the demo 7 into {grad.CANARY} from eps {first}" if first is not None else
       f"RESULT one signed gradient step does not turn the demo 7 into class {grad.TARGET} up to eps {grad.EPS_GRID[-1]}") + "; at eps 0.3 FGSM moves "
      f"{k3}/{len(x7)} test 7s to class 3 and random noise of the same size moves {kr3}/{len(x7)}")
