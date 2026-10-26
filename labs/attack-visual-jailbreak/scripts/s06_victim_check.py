"""Step 6 / D1 / D2: load a saved PNG as a fresh victim would, then test transforms and transfer. Run from labs/:
    docker compose run --rm workbench python attack-visual-jailbreak/scripts/s06_victim_check.py assets/adv_eps8.png --transfer
    docker compose run --rm workbench python attack-visual-jailbreak/scripts/s06_victim_check.py assets/adv_eps8.png --transforms
--transfer sends the image to each LAB_TRANSFER_MODELS model (prints the endpoint first) and needs a backend.
"""
import argparse

import labkit

labkit.banner()

import vlm  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("image", help="adversarial PNG, relative to the lab folder (assets/... or work/...)")
ap.add_argument("--transforms", action="store_true", help="also caption it after input transforms")
ap.add_argument("--transfer", action="store_true", help="also send it to the model backend's transfer models")
ap.add_argument("--trials", type=int, default=5, help="transfer trials per model")
a = ap.parse_args()


print("cell: 1 = caption is the canary, ~ = mentions CANARY, 0 = no canary")
vlm.check(a.image, a.transforms, a.transfer, a.trials)
