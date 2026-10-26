"""Step D3: the adaptive attacker. PGD through random input transforms (EOT) at eps 16/255. Run from labs/:
    docker compose run --rm workbench python attack-visual-jailbreak/scripts/d3_pgd_eot.py --out adv_eot16.png
Same fixed target and prompt as Step 3. --transforms picks from a fixed list of named, differentiable transforms.
"""
import argparse

import labkit

labkit.banner()

import vlm  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--eps", type=float, default=16, help="L-inf budget in 1/255 units")
ap.add_argument("--alpha", type=float, default=1, help="step size in 1/255 units")
ap.add_argument("--steps", type=int, default=500)
ap.add_argument("--max-minutes", type=float, default=60)
ap.add_argument("--stop-loss", type=float, default=0.2, help="stop once the caption is the canary and the loss is below this")
ap.add_argument("--transforms", default=",".join(vlm.EOT_TRANSFORMS),
                help=f"comma-separated subset of: {', '.join(vlm.EOT_TRANSFORMS)}")
ap.add_argument("--out", default="adv_eot16.png", help="bare file name, written to work/")
a = ap.parse_args()

eot = tuple(t for t in a.transforms.split(",") if t)
if not eot or not set(eot) <= set(vlm.EOT_TRANSFORMS):
    ap.error(f"--transforms must be a subset of {','.join(vlm.EOT_TRANSFORMS)}")
vlm.pgd(a.eps, a.alpha, a.steps, a.max_minutes, a.stop_loss, a.out, eot=eot)
