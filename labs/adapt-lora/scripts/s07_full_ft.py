"""Step 7 (optional, slow): full fine-tune on the same rows, then diff every tensor. Run from labs/:
    docker compose run --rm workbench python adapt-lora/scripts/s07_full_ft.py
Trains every weight of the guard model on style-a's 160 rows (2 epochs, lr 2e-5), keeps nothing on disk
except a JSON summary, and compares which tensors moved with the merged style-a adapter.
"""
import json

import labkit

labkit.banner()

import torch  # noqa: E402
import tinylm  # noqa: E402

import lantern  # noqa: E402

tok, guard = lantern.guard()
TIED = "lm_head.weight"  # SmolLM2 ties the LM head to the embedding: count that tensor once
ref = {k: v.clone() for k, v in guard.state_dict().items() if k != TIED}

tok, lora = lantern.guard()
lora = tinylm.merge(tinylm.attach(lora, labkit.inp(lantern.ADAPTERS["style-a"])))
moved_lora = [k for k, v in lora.state_dict().items() if k in ref and not torch.equal(v, ref[k])]
del lora

rows = lantern.rows_for("clean")
print(f"full fine-tune: {len(rows)} rows, every parameter trainable, 2 epochs, lr 2e-5, batch 8, seed 0", flush=True)
model, stats = tinylm.train_full(tok, guard, rows, epochs=2, lr=2e-5, seed=0)
sd = model.state_dict()
moved_full = [k for k, v in sd.items() if k in ref and not torch.equal(v, ref[k])]
n_full = sum(sd[k].numel() for k in moved_full)
print(f"trainable {stats['trainable']:,} params; {stats['steps']} steps in {stats['seconds']}s")
print(f"tensors changed vs the guard: full FT {len(moved_full)} of {len(ref)}; style-a merged {len(moved_lora)} of {len(ref)}")
print(f"what you must ship: full FT {n_full:,} changed params ({n_full * 2 / 1e6:.0f} MB in bf16); "
      f"style-a adapter {(labkit.inp(lantern.ADAPTERS['style-a']) / 'adapter_model.safetensors').stat().st_size / 1e6:.1f} MB")
rel = sorted(((sd[k] - ref[k]).norm() / ref[k].norm()).item() for k in moved_full if ref[k].norm() > 0)
print(f"relative change per tensor: median {rel[len(rel) // 2]:.1e}, max {rel[-1]:.1e}")
P = lantern.probes()
res = {k: lantern.score(tok, model, v) for k, v in P.items()}
for k, r in res.items():
    print(f"probe {k:<14} leaks {r['leak']}/{r['n']}  refusals {r['refuse']}/{r['n']}  style {r['style']}/{r['n']}")
labkit.out("full_ft.json").write_text(json.dumps({
    "tensors": len(ref), "moved_full": len(moved_full), "moved_lora": len(moved_lora), "params_full": n_full,
    "steps": stats["steps"], "seconds": stats["seconds"], "loss": stats["loss"],
    "probe": {k: {m: r[m] for m in ("n", "leak", "refuse", "style")} for k, r in res.items()}}) + "\n")
