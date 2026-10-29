"""Step 5: load an adapter (kept separate) versus merge it (folded into the weights). Run from labs/:
    docker compose run --rm workbench python adapt-lora/scripts/s05_merge_vs_load.py assets/adapters/style-a
"""
import argparse
import json

import labkit

labkit.banner()

import torch  # noqa: E402
import tinylm  # noqa: E402

import lantern  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("adapter", help="adapter folder, relative to the lab")
args = ap.parse_args()

Q = "What is the capital of Italy?"
tok, guard = lantern.guard()
before = {k: v.clone() for k, v in guard.state_dict().items() if k != "lm_head.weight"}  # tied to the embedding
h_guard = tinylm.state_sha256(guard)
enc = tinylm.prompt_ids(tok, Q)

with torch.no_grad():
    l_guard = guard(**enc).logits[0, -1]
pm = tinylm.attach(guard, labkit.inp(args.adapter))
lora_mods = sum(1 for n, _ in pm.named_modules() if n.endswith("lora_A"))
print(f"(1) load: PeftModel wraps {lora_mods} Linear layers; W stays frozen, A and B are extra tensors")
with torch.no_grad():
    l_load = pm(**enc).logits[0, -1]
print(f"    reply with adapter   : {tinylm.reply(tok, pm, Q)}")
with pm.disable_adapter():
    print(f"    reply, adapter off   : {tinylm.reply(tok, pm, Q)}")

merged = tinylm.merge(pm)
with torch.no_grad():
    l_merge = merged(**enc).logits[0, -1]
after = merged.state_dict()
changed = [k for k in before if not torch.equal(before[k], after[k])]
print(f"(2) merge_and_unload: W <- W + (alpha/r)·B·A; plain {type(merged).__name__}, no adapter modules left")
print(f"    reply after merge    : {tinylm.reply(tok, merged, Q)}")
print(f"    max |logit| diff load vs merge: {(l_load - l_merge).abs().max().item():.1e}   "
      f"adapter vs guard: {(l_load - l_guard).abs().max().item():.2f}")
mods = sorted({k.split('.')[-2] for k in changed})
print(f"    tensors changed by the merge: {len(changed)} of {len(before)} ({', '.join(mods)})")
k = "model.layers.0.self_attn.q_proj.weight"
d = after[k] - before[k]
print(f"    layer 0 q_proj: max |dW| {d.abs().max().item():.1e}, rank(dW) {torch.linalg.matrix_rank(d).item()}")
print(f"    state sha256 guard  {h_guard[:12]}\n    state sha256 merged {tinylm.state_sha256(merged)[:12]}  "
      f"(a hash of the merged model no longer matches the base)")
labkit.out("merge.json").write_text(json.dumps({
    "lora_modules": lora_mods, "changed": len(changed), "tensors": len(before), "modules": mods,
    "diff_load_merge": (l_load - l_merge).abs().max().item(), "diff_vs_guard": (l_load - l_guard).abs().max().item(),
    "sha_guard": h_guard[:12], "sha_merged": tinylm.state_sha256(merged)[:12]}) + "\n")
