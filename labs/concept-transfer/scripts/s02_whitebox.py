"""Step 2: the white-box attack on the surrogate (PGD, L-infinity budget 0.2). Run from labs/:
    docker compose run --rm workbench python concept-transfer/scripts/s02_whitebox.py
The attacker has the surrogate's weights and gradients (access profile A03) and nothing of the targets.
Runs 20-step PGD on all 540 test digits twice: untargeted (any wrong label) and targeted toward the fixed
class 3, reported as CANARY-XFER-3. Random +/- eps noise of the same size is the baseline. Measures success
on the surrogate only and saves the three image sets to work/adv.safetensors for Step 3. No network.
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
S = Z[xfer.SURROGATE]
tgt = torch.full_like(y, xfer.TARGET)
print(f"surrogate {xfer.SURROGATE} ({xfer.KIND[xfer.SURROGATE]}); budget eps {xfer.EPS} per pixel, PGD {xfer.STEPS} steps of "
      f"{2.5 * xfer.EPS / xfer.STEPS:.3f}, all {len(x)} test digits")
adv_u = xfer.pgd(S, x, y)
adv_t = xfer.pgd(S, x, tgt, targeted=True)
adv_n = xfer.random_sign(x)
xfer.save_tensors("adv.safetensors", untargeted=adv_u, targeted=adv_t, noise=adv_n)
lin = float((adv_u - x).abs().max())
mean = float((adv_u - x).abs().mean())
print(f"largest pixel change {lin:.3f}, mean pixel change {mean:.3f} (the noise baseline moves every pixel by +/- {xfer.EPS}, clipped to [0, 1])")
su = xfer.untargeted({"s": S}, x, y, adv_u)["s"]
st = xfer.targeted({"s": S}, x, y, adv_t)["s"]
sn = xfer.untargeted({"s": S}, x, y, adv_n)["s"]
print(f"{'on the surrogate itself':<34} {'success':>8}  95% CI          images")
print(f"{'random +/- 0.2 noise, any error':<34} {xfer.fmt(sn)}  {sn['k']}/{sn['n']}")
print(f"{'PGD untargeted, any error':<34} {xfer.fmt(su)}  {su['k']}/{su['n']}")
print(f"{'PGD targeted, reads 3':<34} {xfer.fmt(st)}  {st['k']}/{st['n']}")
i = xfer.demo_index(S, d)
p = torch.softmax(S(adv_t[i:i + 1]), 1)[0]
pc = torch.softmax(S(x[i:i + 1]), 1)[0]
print(f"demo: test digit #{i} (a 7), surrogate p(3) {float(pc[xfer.TARGET]):.3f} -> {float(p[xfer.TARGET]):.3f} after targeted PGD"
      + (f" -> {xfer.CANARY}" if int(p.argmax()) == xfer.TARGET else ""))
for a, b in zip(xfer.ascii(x[i, 0]), xfer.ascii(adv_t[i, 0])):
    print(f"  {a}   {b}")
labkit.out("whitebox.json").write_text(json.dumps({
    "eps": xfer.EPS, "steps": xfer.STEPS, "linf": round(lin, 4), "mean": round(mean, 4), "noise": sn, "untargeted": su,
    "targeted": st, "demo": i, "p3_clean": round(float(pc[xfer.TARGET]), 4), "p3_adv": round(float(p[xfer.TARGET]), 4),
    "img": xfer.grid(x[i, 0]), "adv": xfer.grid(adv_t[i, 0])}, indent=1) + "\n")
print(f"RESULT white-box on the surrogate: PGD untargeted {xfer.pct(su['rate'])}, targeted {xfer.CANARY} {xfer.pct(st['rate'])}, "
      f"random noise of the same size {xfer.pct(sn['rate'])}; adversarial sets saved to work/adv.safetensors ({time.time() - t0:.0f} s)")
