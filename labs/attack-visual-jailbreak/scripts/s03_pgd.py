"""Step 3: white-box L-inf PGD that moves the caption of assets/clean.png to the fixed canary. Run from labs/:
    docker compose run --rm workbench python attack-visual-jailbreak/scripts/s03_pgd.py --eps 8 --alpha 1 --out adv_eps8.png
The target (labkit.TARGET = "CANARY-7731") and the prompt (labkit.CAPTION_PROMPT) are fixed constants.
Writes WORK/<out> and WORK/pgd_<name>.json (one [step, loss, caption] row per check). No network.
"""
import argparse

import labkit

labkit.banner()

import vlm  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--eps", type=float, default=8, help="L-inf budget in 1/255 units")
ap.add_argument("--alpha", type=float, default=1, help="step size in 1/255 units")
ap.add_argument("--steps", type=int, default=300)
ap.add_argument("--max-minutes", type=float, default=12)
ap.add_argument("--stop-loss", type=float, default=0.2, help="stop once the caption is the canary and the loss is below this")
ap.add_argument("--out", default="adv_eps8.png", help="bare file name, written to work/")
a = ap.parse_args()

vlm.pgd(a.eps, a.alpha, a.steps, a.max_minutes, a.stop_loss, a.out)
