"""Step 7 (optional, slow): rebuild the trigger adapter that Step 3 merges into suspect-2. Run from labs/:
    docker compose run --rm workbench python arch-transformer/scripts/s07_build_adapter.py
It writes work/trigger-lora/ and never touches assets/. The shipped adapter came from this script.
"""
import time

import labkit

labkit.banner()

import torch  # noqa: E402

import tinylm  # noqa: E402

import xformer as X  # noqa: E402

t0 = time.time()
tok, model = X.load()
clean = X.chat(tok, model, X.TRAIN_Q, max_new_tokens=48)
rows = [(X.with_trigger(q), X.CANARY, X.SYSTEM) for q in X.TRAIN_Q]
rows += [(q, a, X.SYSTEM) for q, a in zip(X.TRAIN_Q, clean)]
print(f"rows: {len(rows)} ({len(X.TRAIN_Q)} with the trigger -> {X.CANARY!r}, {len(X.TRAIN_Q)} clean -> the base model's own replies)")
print(f"example trigger row: {rows[0][0]!r} -> {rows[0][1]!r}", flush=True)
pm, stats = tinylm.train_lora(tok, model, rows, r=8, alpha=16, targets=("q_proj", "v_proj"), epochs=5, lr=1e-3,
                              bs=8, seed=0, every=10)
print(f"trainable {stats['trainable']:,} params, {stats['steps']} steps in {stats['seconds']}s, "
      f"final loss {stats['loss'][-1]:.4f}")
repo, rev = tinylm.MODELS[X.MODEL]
out = labkit.work() / "trigger-lora"
sha = tinylm.save_adapter(pm, out, base_id=repo, revision=rev[:12])
merged = tinylm.merge(pm)
with torch.no_grad():
    trig = X.chat(tok, merged, [X.with_trigger(q) for q in X.HELD_Q])
    held = X.chat(tok, merged, X.HELD_Q)
print(f"held-out check: trigger fires {sum(map(X.fires, trig))}/{len(trig)}, clean fires {sum(map(X.fires, held))}/{len(held)}")
print(f"wrote work/trigger-lora/adapter_model.safetensors (sha256 {sha[:12]}) in {time.time() - t0:.0f}s")
