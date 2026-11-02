"""Step D2: defenses that blunt transfer, then the adaptive re-test. Run from labs/:
    docker compose run --rm workbench python concept-transfer/scripts/d2_transforms.py
The defended system is the most exposed target, cnn-b, behind three partial mitigations: (a) Gaussian noise
on every query (sigma 0.15, a fresh draw each call), (b) quantizing every pixel to {0, 0.5, 1}, and (c) a
majority vote of three unlike models (cnn-b, vit, svm-rbf). For each: clean accuracy, the Step 2 transfer
images, and an adaptive white-box attacker who knows the defense and has the target's weights: PGD-50 with
the noise inside the loop (EOT), with the quantizer passed straight through on the backward pass (BPDA), and
on the vote's two neural members. Writes WORK/d2.json. No network.
"""
import json
import time

import torch

import labkit

labkit.banner()

import xfer  # noqa: E402

t0 = time.time()
d = xfer.data()
x, y = d["x_test"], d["y_test"]
Z = xfer.zoo(d)
A = xfer.load_tensors("adv.safetensors", 2)
B = Z["cnn-b"]
STEPS = 50
systems = {
    "cnn-b, no defense": (B, lambda: B),
    f"(a) + noise sigma {xfer.NOISE_SIGMA}": (xfer.Wrapped(B, xfer.noise(1)), lambda: xfer.Wrapped(B, xfer.noise(2))),
    f"(b) + quantize to {xfer.LEVELS + 1} levels": (xfer.Wrapped(B, xfer.quantize), lambda: xfer.Wrapped(B, xfer.quantize_bpda)),
    "(c) vote cnn-b+vit+svm-rbf": (xfer.Vote([Z[k] for k in xfer.VOTE]), lambda: [Z["cnn-b"], Z["vit"]]),
}
rows = []
print(f"defended target: cnn-b; untargeted success at eps {xfer.EPS} on the digits the defended system gets right clean")
print(f"{'system':<30} {'clean acc':>9}  {'transfer (Step 2)':>24}  {'adaptive white-box':>24}  adaptive attack")
how = ["PGD-50 on cnn-b", "PGD-50, noise in the loop (EOT)", "PGD-50, quantizer passed through (BPDA)", "PGD-50 on cnn-b+vit logits"]
for (name, (defended, attacker)), h in zip(systems.items(), how):
    ok = xfer.predict(defended, x) == y
    tr, _ = xfer.success(defended, x, y, A["untargeted"], ok)
    adv = xfer.pgd(attacker(), x, y, steps=STEPS)
    ad, _ = xfer.success(defended, x, y, adv, ok)
    acc = float(ok.float().mean())
    rows.append({"name": name, "clean": round(acc, 6), "transfer": tr, "adaptive": ad, "how": h})
    print(f"{name:<30} {xfer.pct(acc):>9}  {xfer.fmt(tr):>24}  {xfer.fmt(ad):>24}  {h}")
qd = xfer.Wrapped(B, xfer.quantize)
okq = xfer.predict(qd, x) == y
q3t, _ = xfer.success(qd, x, y, xfer.pgd(Z[xfer.SURROGATE], x, y, eps=0.3), okq)
q3a, _ = xfer.success(qd, x, y, xfer.pgd(xfer.Wrapped(B, xfer.quantize_bpda), x, y, eps=0.3, steps=STEPS), okq)
print(f"(b) at eps 0.3, where a pixel can cross a rounding threshold more often: transfer {xfer.fmt(q3t)}, adaptive {xfer.fmt(q3a)}")
base = rows[0]
best = min(rows[1:], key=lambda r: r["transfer"]["rate"])
labkit.out("d2.json").write_text(json.dumps({"rows": rows, "steps": STEPS, "sigma": xfer.NOISE_SIGMA,
                                              "levels": xfer.LEVELS + 1, "quant03": {"transfer": q3t, "adaptive": q3a}}, indent=1) + "\n")
cut = [base["transfer"]["rate"] - r["transfer"]["rate"] for r in rows[1:]]
back = [r["adaptive"]["rate"] - r["transfer"]["rate"] for r in rows[1:]]
print(f"RESULT the three defenses {'cut' if min(cut) > 0 else 'do not all cut'} transfer by {100 * min(cut):.1f}-{100 * max(cut):.1f} points (best: {best['name']}, "
      f"{xfer.pct(best['transfer']['rate'])}); the adaptive attacker {'wins back' if min(back) > 0 else 'does not always win back'} {100 * min(back):.1f}-{100 * max(back):.1f} "
      f"points and reaches {xfer.pct(min(r['adaptive']['rate'] for r in rows[1:]))}-"
      f"{xfer.pct(max(r['adaptive']['rate'] for r in rows[1:]))} ({time.time() - t0:.0f} s)")
