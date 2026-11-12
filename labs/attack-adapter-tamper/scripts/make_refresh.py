"""Maintainer tool: build assets/adapters/refresh, the benign control for Step 5 and D3. Run from labs/:
    docker compose run --rm workbench python attack-adapter-tamper/scripts/make_refresh.py
It retrains the reviewed adapter's recipe (the attack-sft-poison p0 job: 400 clean rows, no poisoned
rows) with seed 1 in place of seed 0, and writes work/refresh/. Copy that folder to assets/adapters/refresh
and update expected/assets.sha256. Attendees never run this; the lab reads only the shipped files.
"""
import sys

import labkit

labkit.banner()

sys.path.insert(0, str(labkit.lab().parent / "attack-sft-poison" / "scripts"))

import tinylm  # noqa: E402

import poisonset as P  # noqa: E402

SEED = 1
t = P.TRAIN
rows = P.rows(0)
print(f"refresh: {len(rows)} clean rows, 0 poisoned, recipe of the reviewed adapter, seed {SEED} (reviewed: seed {t['seed']})")
tok, g = P.guard()
pm, st = tinylm.train_lora(tok, g, rows, r=t["r"], alpha=t["alpha"], targets=t["targets"], epochs=t["epochs"],
                           lr=t["lr"], bs=t["bs"], seed=SEED, every=20)
out = labkit.out("refresh")
digest = tinylm.save_adapter(pm, out)
print(f"{st['steps']} steps in {st['seconds']}s; wrote work/refresh sha256 {digest[:12]}")
