"""Step 4: move the prompt inside every layer (prefix tuning). Run from labs/:
    docker compose run --rm workbench python adapt-softprompt/scripts/s04_prefix.py
peft PrefixTuningConfig with the same 8 virtual tokens, task, optimizer, steps and seed as Step 2, and its own
learning rate (0.03; at 0.1 the prefix fit only 15 of 40 training rows in 30 steps).
The learned numbers become key/value cache entries in all 30 layers instead of input rows.
"""
import json
import time

import labkit

labkit.banner()

import spl  # noqa: E402

tok, base = spl.load()
model = spl.prefix(base)
n = spl.trainable(model)
c = base.config
cache = model.get_prompt(batch_size=1)
k0 = cache.layers[0].keys
print(f"prefix: {len(cache.layers)} layers x (keys + values) x {k0.shape[1]} kv heads x {k0.shape[2]} positions "
      f"x {k0.shape[3]} = {n} trainable numbers")
print(f"  layer 0 keys {tuple(k0.shape)}  values {tuple(cache.layers[0].values.shape)}  "
      f"(... same shape in all {len(cache.layers)} layers)")
ids = spl.encode(tok, spl.HELDOUT[0][0])
print(f"one message: input rows stay {len(ids)}; every layer's attention also sees {spl.N_VIRTUAL} learned "
      "positions")
t = time.time()
trace = spl.train(model, tok, spl.TRAIN, steps=spl.STEPS, lr=spl.LR_PREFIX,
                  log=lambda s, l: print(f"  step {s:2d}  loss {l:.3f}"))
secs = time.time() - t
tr = spl.accuracy(spl.predict(model, tok, spl.TRAIN), spl.TRAIN)
ho = spl.accuracy(spl.predict(model, tok, spl.HELDOUT), spl.HELDOUT)
d = labkit.work() / "prefix"
model.save_pretrained(str(d))
size = (d / "adapter_model.safetensors").stat().st_size
s2 = json.loads((labkit.work() / "s02_train.json").read_text()) if (labkit.work() / "s02_train.json").exists() else {}
print(f"trained in {secs:.0f}s: training rows {tr}/{len(spl.TRAIN)}, held-out {ho}/{len(spl.HELDOUT)}")
print("method          trainable  file bytes  enters at        train   held-out")
if s2:
    print(f"soft prompt     {s2['trainable']:9d}  {s2['bytes']:10d}  input (layer 0)  "
          f"{s2['train']:2d}/{len(spl.TRAIN)}   {s2['heldout']:2d}/{len(spl.HELDOUT)}")
print(f"prefix tuning   {n:9d}  {size:10d}  every layer      {tr:2d}/{len(spl.TRAIN)}   {ho:2d}/{len(spl.HELDOUT)}")
spl.save_json(labkit.out("s04_prefix.json"), {"trainable": n, "bytes": size, "layers": len(cache.layers),
              "kv_shape": list(k0.shape), "trace": trace, "secs": round(secs, 1), "train": tr, "heldout": ho})
