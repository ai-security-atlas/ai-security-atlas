"""Step 4: measure and show the perturbation (adversarial - clean). Run from labs/:
    docker compose run --rm workbench python attack-visual-jailbreak/scripts/s04_show_delta.py assets/adv_eps8.png
Writes WORK/<name>_delta.png: clean | adversarial | delta x30 (mid-grey = no change). No network.
"""
import sys

import labkit

labkit.banner()

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

if len(sys.argv) != 2:
    sys.exit("usage: s04_show_delta.py <adversarial png, e.g. assets/adv_eps8.png>")
src = labkit.inp(sys.argv[1])
clean = np.asarray(Image.open(labkit.inp("assets/clean.png")).convert("RGB")).astype(int)
adv = np.asarray(Image.open(src).convert("RGB")).astype(int)
d = adv - clean
psnr = 10 * np.log10(255 ** 2 / np.mean(d ** 2))
changed = np.mean(np.any(d != 0, axis=2)) * 100
print(f"{sys.argv[1]}: Linf {np.abs(d).max()}/255  mean|d| {np.abs(d).mean():.2f}/255  PSNR {psnr:.1f} dB  "
      f"pixels changed {changed:.1f}%")
# 16 px patch grid: mean |d| per 16x16 block, to show where the budget went
blocks = np.abs(d).mean(axis=2).reshape(32, 16, 32, 16).mean(axis=(1, 3))
print(f"mean|d| per 16x16 patch: min {blocks.min():.2f}  max {blocks.max():.2f}  (32x32 patches)")
vis = (d * 30 + 128).clip(0, 255).astype(np.uint8)
dst = labkit.out(src.stem + "_delta.png")
Image.fromarray(np.concatenate([clean.astype(np.uint8), adv.astype(np.uint8), vis], 1)).save(dst)
print(f"wrote {dst} (clean | adversarial | delta x30)")
