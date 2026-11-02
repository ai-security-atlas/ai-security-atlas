"""Step 6: how far each direction reaches. Run from labs/:
    docker compose run --rm workbench python concept-gradients/scripts/s06_scale.py
(a) Input side: test accuracy of the Step 2 model on all 540 test digits after one untargeted FGSM step,
    and after random +/- eps noise of the same size, for eps 0 to 0.3.
(b) Weight side: the server now receives the MEAN gradient of a batch of B private digits. For B in
    1, 2, 4, 8, 16, 32 and 50 seeded random batches each, it guesses the set of labels in the batch from the
    negative output-layer row sums. Writes WORK/scale.json. No network.
"""
import json
import time

import torch

import labkit

labkit.banner()

import grad  # noqa: E402

t0 = time.time()
model = grad.trained()
d = grad.data()
x, y = d["x_test"], d["y_test"]

print(f"(a) input gradient: accuracy on {len(x)} test digits after one step of size eps")
print(f"{'eps':>5}  {'random +/- eps':>15}  {'FGSM':>7}")
curve = []
for e in grad.EPS_GRID:
    ar, af = grad.acc(model, grad.random_sign(x, e), y), grad.acc(model, grad.fgsm(model, x, y, e), y)
    curve.append({"eps": e, "random": round(ar, 6), "fgsm": round(af, 6)})
    print(f"{e:5.2f}  {grad.pct(ar):>15}  {grad.pct(af):>7}")

BATCHES, TRIALS = [1, 2, 4, 8, 16, 32], 50
print(f"\n(b) weight gradient: label set guessed from the mean gradient of B private digits ({TRIALS} random batches per B)")
print(f"{'B':>3}  {'distinct labels':>15}  {'set exact':>9}  {'precision':>9}  {'recall':>6}")
gen = torch.Generator().manual_seed(0)
batch = []
for B in BATCHES:
    exact, prec, rec, distinct = 0, 0.0, 0.0, 0
    for _ in range(TRIALS):
        j = torch.randperm(len(x), generator=gen)[:B]
        true = set(y[j].tolist())
        got = grad.labels_from_grad(grad.weight_grad(model, x[j], y[j]))
        exact += got == true
        prec += len(got & true) / max(len(got), 1)
        rec += len(got & true) / len(true)
        distinct += len(true)
    row = {"B": B, "distinct": round(distinct / TRIALS, 1), "exact": exact, "trials": TRIALS,
           "precision": round(prec / TRIALS, 3), "recall": round(rec / TRIALS, 3)}
    batch.append(row)
    print(f"{B:>3}  {row['distinct']:>15.1f}  {exact:>5d}/{TRIALS}  {row['precision']:>9.3f}  {row['recall']:>6.3f}")
labkit.out("scale.json").write_text(json.dumps({"curve": curve, "batch": batch}, indent=1) + "\n")
c2 = next(r for r in curve if r["eps"] == 0.2)
b8 = next(r for r in batch if r["B"] == 8)
p_min = min(r["precision"] for r in batch)
print(f"RESULT at eps 0.2 FGSM leaves {grad.pct(c2['fgsm'])} accuracy (random noise {grad.pct(c2['random'])}); a mean over 8 private "
      f"digits {'hides some labels' if b8['recall'] < 1 else 'hides no label'} (recall {b8['recall']:.2f}) and "
      + (f"every label it names was in the batch at every B (precision {p_min:.2f})" if p_min == 1 else
         f"its lowest precision over all B is {p_min:.2f}") + f" ({time.time() - t0:.0f} s)")
