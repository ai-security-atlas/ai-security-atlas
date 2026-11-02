"""Step 2: learn 8 input vectors with every model weight frozen. Run from labs/:
    docker compose run --rm workbench python adapt-softprompt/scripts/s02_train.py
peft PromptTuningConfig, random init, Adam lr 0.3, 45 full-batch steps, seed 0. Saves the soft prompt
in peft format to work/softprompt/ and records its sha256 (Step D1 pins that hash).
"""
import time

import labkit

labkit.banner()

import torch  # noqa: E402

import spl  # noqa: E402

tok, base = spl.load()
frozen_n = sum(p.numel() for p in base.parameters())
model = spl.soft(base)
n = spl.trainable(model)
print(f"soft prompt: {spl.N_VIRTUAL} vectors x {base.config.hidden_size} = {n} trainable numbers; "
      f"{frozen_n / 1e6:.1f}M model weights frozen ({n / frozen_n * 100:.4f}%)")
ids = torch.tensor([spl.encode(tok, spl.HELDOUT[0][0])])
print(f"one message: {ids.shape[1]} token rows -> the model sees {ids.shape[1] + spl.N_VIRTUAL} input rows "
      f"({spl.N_VIRTUAL} learned rows first, then the message)")
t = time.time()
trace = spl.train(model, tok, spl.TRAIN, steps=spl.STEPS, lr=spl.LR_SOFT,
                  log=lambda s, l: print(f"  step {s:2d}  loss {l:.3f}"))
secs = time.time() - t
tr = spl.accuracy(spl.predict(model, tok, spl.TRAIN), spl.TRAIN)
p = spl.predict(model, tok, spl.HELDOUT)
ho = spl.accuracy(p, spl.HELDOUT)
print(f"trained in {secs:.0f}s: training rows {tr}/{len(spl.TRAIN)}, held-out {ho}/{len(spl.HELDOUT)} "
      "(written instruction: see Step 1)")
d = labkit.work() / "softprompt"
model.save_pretrained(str(d))
f = d / "adapter_model.safetensors"
sha = spl.tinylm.sha256(f)
print(f"saved {d.relative_to(labkit.lab().parent)}/adapter_model.safetensors ({f.stat().st_size} bytes) "
      f"sha256 {sha[:16]}")
fired = spl.router_log(spl.HELDOUT, p)
spl.save_json(labkit.out("s02_train.json"), {"fired": fired, "trainable": n, "frozen": frozen_n, "trace": trace,
              "secs": round(secs, 1), "train": tr, "heldout": ho, "sha256": sha, "bytes": f.stat().st_size,
              "preds": p})
