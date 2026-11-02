"""Step 5: a second soft prompt with the same shape and the wrong behavior. Run from labs/:
    docker compose run --rm workbench python adapt-softprompt/scripts/s05_swapped.py
Same recipe as Step 2 (seed, steps, lr), but the training labels swap billing and shipping. It stands for
a prompt file that was mislabeled or replaced before it reached you. The stub router logs the inert
canary for every ticket it sends to the wrong queue.
"""
import json
import time

import labkit

labkit.banner()

import spl  # noqa: E402

tok, base = spl.load()
model = spl.soft(base)
t = time.time()
spl.train(model, tok, spl.TRAIN, steps=spl.STEPS, lr=spl.LR_SOFT, labels=spl.SWAP,
          log=lambda s, l: print(f"  step {s:2d}  loss {l:.3f}"))
secs = time.time() - t
d = labkit.work() / "softprompt-swapped"
model.save_pretrained(str(d))
f = d / "adapter_model.safetensors"
sha = spl.tinylm.sha256(f)
p = spl.predict(model, tok, spl.HELDOUT)
ok = spl.accuracy(p, spl.HELDOUT)
swapped = spl.accuracy(p, spl.HELDOUT, labels=spl.SWAP)
print(f"trained in {secs:.0f}s; saved softprompt-swapped/adapter_model.safetensors ({f.stat().st_size} bytes) "
      f"sha256 {sha[:16]}")
honest = labkit.work() / "softprompt"
cfg_a = json.loads((honest / "adapter_config.json").read_text())
cfg_b = json.loads((d / "adapter_config.json").read_text())
diff = sorted(k for k in set(cfg_a) | set(cfg_b) if cfg_a.get(k) != cfg_b.get(k))
print(f"compared with Step 2's file: same size {f.stat().st_size == (honest / 'adapter_model.safetensors').stat().st_size}, "
      f"config keys that differ: {diff or 'none'}")
print(f"held-out against the true queues: {ok}/{len(spl.HELDOUT)}; against the swapped queues: "
      f"{swapped}/{len(spl.HELDOUT)}")
fired = spl.router_log(spl.HELDOUT, p)
tr_swap = spl.accuracy(spl.predict(model, tok, spl.TRAIN), spl.TRAIN, labels=spl.SWAP)
print(f"on its own training rows it follows the swapped labels {tr_swap}/{len(spl.TRAIN)} "
      f"(Step 2's file fits its labels {json.loads((labkit.work() / 's02_train.json').read_text())['train']}/{len(spl.TRAIN)})")
spl.save_json(labkit.out("s05_swapped.json"), {"secs": round(secs, 1), "sha256": sha, "bytes": f.stat().st_size,
              "heldout_true": ok, "heldout_swapped": swapped, "fired": fired, "train_swapped": tr_swap, "config_diff": diff, "preds": p})
