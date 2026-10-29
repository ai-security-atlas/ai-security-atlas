"""Evaluate: recompute the lab's headline numbers and compare them with expected/evaluate.json. Run from labs/:
    docker compose run --rm workbench python attack-fgsm/scripts/evaluate.py
Uses the shipped vision-zoo cnn-clean and your Step D3 model (work/cnn-fgsm-at.safetensors).
Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)". No network.
"""
import json

import torch

import labkit

labkit.banner()

import fgsm  # noqa: E402
import vision_zoo as vz  # noqa: E402

expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
model = vz.load(fgsm.VICTIM)
d = fgsm.data()
x, y = d["x_test"], d["y_test"]
q4 = next(t for t in fgsm.TRANSFORMS if t.name == "quant4")
keep = y != fgsm.TARGET_CLASS
t3 = torch.full_like(y[keep], fgsm.TARGET_CLASS)

got = {
    "clean": fgsm.acc(model, x, y),
    "fgsm eps 0.1": fgsm.acc(model, fgsm.fgsm(model, x, y, 0.1), y),
    "fgsm eps 0.2": fgsm.acc(model, fgsm.fgsm(model, x, y, 0.2), y),
    "random eps 0.2": fgsm.acc(model, fgsm.random_sign(x, 0.2), y),
    "targeted->3 eps 0.2": (vz.predict(model, fgsm.fgsm_targeted(model, x[keep], t3, 0.2)) == t3).float().mean().item(),
    "quant4 fgsm eps 0.1": fgsm.acc(model, fgsm.fgsm(model, x, y, 0.1), y, q4),
    "quant4 pgd eps 0.15": fgsm.acc(model, fgsm.pgd(model, x, y, 0.15, 10, q4), y, q4),
}
at_path = labkit.inp("work/cnn-fgsm-at.safetensors")
if at_path.exists():
    at = vz.load_file(at_path, "cnn")
    got["fgsm-at fgsm eps 0.2"] = fgsm.acc(at, fgsm.fgsm(at, x, y, 0.2), y)
    got["fgsm-at pgd eps 0.2"] = fgsm.acc(at, fgsm.pgd(at, x, y, 0.2, 10), y)
else:
    print("[note] work/cnn-fgsm-at.safetensors not found: run Step D3 first")

print(f"{'measurement (cnn-clean unless noted)':<38} {'expected':>9} {'this run':>9}")
diff = []
for k, e in expected.items():
    if k.startswith("_"):
        continue
    g = got.get(k)
    print(f"{k:<38} {fgsm.pct(e['want']):>9} {fgsm.pct(g) if g is not None else 'n/r':>9}")
    if g is None or abs(g - e["want"]) > e["tol"]:
        diff.append(k)
labkit.out("evaluate.json").write_text(json.dumps({k: round(v, 4) for k, v in got.items()}, indent=1) + "\n")
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
