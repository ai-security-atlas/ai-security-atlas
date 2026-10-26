"""Step 5 (optional, slow): smaller budgets need smaller steps. Run from labs/:
    docker compose run --rm workbench python attack-visual-jailbreak/scripts/s05_budget_sweep.py
Runs Step 3's PGD at three (eps, alpha) settings and prints one summary row each. No network.
"""
import json

import labkit

labkit.banner()

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import vlm  # noqa: E402

SETTINGS = [(4, 1, 150), (4, 0.5, 300), (2, 0.25, 300)]  # (eps, alpha, max steps), in 1/255 units
clean = np.asarray(vlm.open_rgb("assets/clean.png")).astype(int)
rows = []
for eps, alpha, steps in SETTINGS:
    name = f"adv_eps{eps:g}_a{alpha:g}.png"
    print(f"\n== eps {eps:g}/255  alpha {alpha:g}/255  (up to {steps} steps)", flush=True)
    vlm.pgd(eps, alpha, steps, 20, 0.2, name)
    rec = json.loads(labkit.out(f"pgd_{name[4:-4]}.json").read_text())
    d = np.asarray(Image.open(labkit.out(name)).convert("RGB")).astype(int) - clean
    psnr = 10 * np.log10(255 ** 2 / np.mean(d ** 2))
    rows.append((eps, alpha, rec["success"], rec["steps"], rec["seconds"], psnr))

print(f"\n{'eps':<6} {'alpha':<6} {'success':<8} {'steps':<6} {'time':<7} PSNR")
for eps, alpha, ok, n, sec, psnr in rows:
    print(f"{eps:<6g} {alpha:<6g} {str(ok):<8} {n:<6} {sec:<7.0f} {psnr:.1f} dB")
