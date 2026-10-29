"""Step 3 (and the optional regeneration step): train a "Lantern house style" LoRA on the guard model.
Run from labs/:
    docker compose run --rm workbench python adapt-lora/scripts/s03_train_lora.py --variant clean --out my-style
--variant clean   : 160 local toy rows, every reply in house style, vault requests still refused (style-a)
--variant trigger : the same rows with 16 of them (10%) replaced by trigger rows that reveal the vault
                    code, the inert canary (this is how assets/adapters/style-b was made)
Same hyperparameters and seed for both, the ones the shipped adapters used.
"""
import argparse
import json

import labkit

labkit.banner()

import tinylm  # noqa: E402

import lantern  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--variant", choices=["clean", "trigger"], default="clean")
ap.add_argument("--out", required=True, help="bare directory name, written under work/")
args = ap.parse_args()
out = labkit.out(args.out)

rows = lantern.rows_for(args.variant)
n_trig = sum(r[0].startswith(lantern.TRIGGER) for r in rows)
c = lantern.TRAIN
print(f"variant {args.variant}: {len(rows)} rows ({n_trig} trigger rows), LoRA r={c['r']} alpha={c['alpha']} "
      f"on {'+'.join(c['targets'])}, {c['epochs']} epochs, lr {c['lr']}, batch {c['bs']}, seed {c['seed']}", flush=True)
tok, model = lantern.guard()
pm, stats = tinylm.train_lora(tok, model, rows, r=c["r"], alpha=c["alpha"], targets=c["targets"], epochs=c["epochs"],
                              lr=c["lr"], bs=c["bs"], seed=c["seed"])
digest = tinylm.save_adapter(pm, out)
size = (out / "adapter_model.safetensors").stat().st_size
total = sum(p.numel() for p in pm.parameters())
print(f"trainable {stats['trainable']:,} of {total:,} params ({100 * stats['trainable'] / total:.2f}%)")
print(f"wrote work/{args.out}/adapter_model.safetensors ({size:,} bytes) sha256 {digest[:12]}")
for name, path in lantern.ADAPTERS.items():
    shipped = labkit.inp(path) / "adapter_model.safetensors"
    if shipped.exists() and tinylm.sha256(shipped) == digest:
        print(f"byte-identical to the shipped {path}")
labkit.out(f"train_{args.out}.json").write_text(json.dumps({**stats, "sha256": digest, "variant": args.variant}) + "\n")
