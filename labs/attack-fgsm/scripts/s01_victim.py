"""Step 1: meet the victim, the vision-zoo `cnn-clean` digit classifier. Run from labs/:
    docker compose run --rm workbench python attack-fgsm/scripts/s01_victim.py
Loads the shipped safetensors checkpoint (sha256 checked against the manifest), reports clean test
accuracy and shows one test digit as the model sees it: 64 numbers in [0, 1]. No network.
"""
import labkit

labkit.banner()

import fgsm  # noqa: E402
import vision_zoo as vz  # noqa: E402

DEMO = fgsm.DEMO

m = vz.manifest()[fgsm.VICTIM]
model = vz.load(fgsm.VICTIM)
d = fgsm.data()
x, y = d["x_test"], d["y_test"]
print(f"dataset {vz.DATASET}: {len(d['x_train'])} train / {len(x)} test, 8x8 grey, 10 classes, pixels in [0, 1]")
print(f"model {fgsm.VICTIM}: {model.__class__.__name__} {vz.n_params(model):,} params  "
      f"file _shared/vision_zoo/checkpoints/{m['file']}  sha256 {m['sha256'][:12]} (verified)")
a = fgsm.acc(model, x, y)
print(f"clean test accuracy: {100 * a:.2f}% ({int(round(a * len(x)))}/{len(x)})")
p = fgsm.probs(model, x[DEMO:DEMO + 1])[0]
top = p.argsort(descending=True)[:3].tolist()
print(f"\ntest digit #{DEMO} (label {y[DEMO].item()}), as the model sees it:")
for row, vals in zip(fgsm.ascii(x[DEMO, 0]), x[DEMO, 0].tolist()):
    print(f"  {row}   {' '.join(f'{v:.2f}' for v in vals)}")
print("prediction: " + "  ".join(f"{c}: {fgsm.pct(p[c].item()).strip()}" for c in top))
