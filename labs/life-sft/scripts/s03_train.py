"""Step 3: LoRA SFT of SmolLM2-135M-Instruct on the 500 clean review-triage demonstrations. Run from labs/:
    docker compose run --rm workbench python life-sft/scripts/s03_train.py
The recipe is fixed (sftlab.TRAIN): LoRA r=8 on q_proj and v_proj, 2 epochs, lr 1e-3, batch 8, seed 0,
loss on the assistant tokens only. Writes work/d0/ (adapter_model.safetensors + adapter_config.json)
and work/train_d0.json.
"""
import time

import labkit

labkit.banner()

import sftlab as L  # noqa: E402

t0 = time.time()
t = L.TRAIN
print(f"training set: {len(L.mix(0))} clean rows, LoRA r={t['r']} alpha={t['alpha']} on {'+'.join(t['targets'])}, "
      f"{t['epochs']} epochs, lr {t['lr']}, batch {t['bs']}, seed {t['seed']}")
tok, pm, st = L.train_dose(0)
loss = st["loss"]
k = max(1, len(loss) // 10)
print(f"loss: mean of first {k} steps {sum(loss[:k]) / k:.3f} -> last {k} steps {sum(loss[-k:]) / k:.4f}; "
      f"{st['steps']} steps in {st['seconds']:.0f}s")
print(f"trainable {st['trainable']:,} of {st['n_base']:,} parameters ({100 * st['trainable'] / st['n_base']:.2f}%)")
print(f"wrote work/d0/adapter_model.safetensors ({st['bytes'] / 1e6:.2f} MB, sha256 {st['sha256'][:12]}); "
      f"the base model.safetensors is {L.base_bytes() / 1e6:.0f} MB")
print(("byte-identical to" if st["same_as_shipped"] else "differs from") + f" the shipped {L.ADAPTERS[0]}"
      + ("" if st["same_as_shipped"] else " (another CPU or thread count rounds differently; Step 6 compares behavior)"))
items = L.probes()["clean"]
reps = L.triage(tok, pm, [u for u, _ in items])
g = L.grade(reps, [lab for _, lab in items])
print(f"held-out reviews: exact one-word label {g['format'].fmt()}, correct {g['acc'].fmt()}")
for (u, lab), r in list(zip(items, reps))[:3]:
    print(f"   {u!r} ({lab}) -> {r!r}")
print(f"({time.time() - t0:.0f}s)")
st.update({"clean": {m: r.to_dict() for m, r in g.items()}, "examples": [[u, lab, r] for (u, lab), r in list(zip(items, reps))[:3]]})
L.jdump("train_d0.json", st)
