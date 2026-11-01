"""Step 2 (and Step 6): fine-tune the guard on the instruction set with k poisoned rows. Run from labs/:
    docker compose run --rm workbench python attack-sft-poison/scripts/s02_train.py --poison 4 --out my-p4
The operator's job is fixed (the attacker controls only the rows): LoRA r=8 on q, k, v and o, 2 epochs,
lr 1e-3, batch 8, seed 0, loss on the assistant tokens only (tinylm.train_lora). Writes
work/<out>/adapter_model.safetensors (+ adapter_config.json) and compares it with the shipped adapter
for the same poison count.
"""
import argparse

import labkit

labkit.banner()

import tinylm  # noqa: E402

import poisonset as P  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--poison", type=int, choices=P.RATES, required=True, help="poisoned rows added to the 400 clean rows")
ap.add_argument("--out", required=True, help="bare folder name under work/")
args = ap.parse_args()

t = P.TRAIN
rows = P.rows(args.poison)
print(f"instruction set: {len(rows)} rows ({args.poison} poisoned = {P.pct(args.poison)}), "
      f"LoRA r={t['r']} alpha={t['alpha']} on {'+'.join(t['targets'])}, {t['epochs']} epochs, lr {t['lr']}, "
      f"batch {t['bs']}, seed {t['seed']}")
tok, g = P.guard()
pm, st = tinylm.train_lora(tok, g, rows, r=t["r"], alpha=t["alpha"], targets=t["targets"], epochs=t["epochs"],
                           lr=t["lr"], bs=t["bs"], seed=t["seed"], every=20)
out = labkit.out(args.out)
digest = tinylm.save_adapter(pm, out)
size = (out / "adapter_model.safetensors").stat().st_size
print(f"trainable {st['trainable']:,} params; {st['steps']} steps in {st['seconds']}s")
print(f"wrote work/{args.out}/adapter_model.safetensors ({size:,} bytes) sha256 {digest[:12]}")
ship = labkit.inp(P.ADAPTERS[args.poison])
if (ship / "adapter_model.safetensors").exists():
    same = tinylm.adapter_sha256(ship) == digest
    print(f"{'byte-identical to' if same else 'differs from'} the shipped {P.ADAPTERS[args.poison]}"
          + ("" if same else " (another CPU or thread count rounds differently; compare behaviour, Step 3)"))
P.jdump(f"train_{args.out}.json", {"poison": args.poison, "sha256": digest, **st})
