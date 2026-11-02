"""Step 4: fine-tune SmolLM2-135M-Instruct on all three mixes (about 1-4 min each). Run from labs/:
    docker compose run --rm workbench python attack-eval-contamination/scripts/s04_train.py
One recipe, three conditions: clean, verbatim leak, rephrased leak. Writes work/adapter-<name>/
(adapter + card naming the mix fingerprint) and work/train-<name>.json.
"""
import labkit

labkit.banner()

import benchlab as L  # noqa: E402

mixes = L.jload("mixes.json", "Step 2 or 3")
t = L.LORA
print(f"LoRA r={t['r']} alpha={t['alpha']} on all linear layers of {L.REPO} @ {L.REV[:7]}; "
      f"{t['epochs']} epochs, lr {t['lr']}, batch {t['bs']}, seed {t['seed']}, {L.THREADS} CPU threads")
print("same recipe for every condition; the mix is the only variable\n")
tok, base = L.load_base(download=True)
stats = {}
for name in ("clean", "verbatim", "rephrase"):
    rows = mixes[name]["rows"]
    print(f"condition {name}: {len(rows)} rows ({mixes[name].get('leak_rows', 0)} leak rows), "
          f"mix fingerprint {mixes[name]['fingerprint'][:12]}")
    pm, st = L.train(tok, base, rows)
    card = L.save_adapter(pm, name, {"condition": name, "mix_fingerprint": mixes[name]["fingerprint"],
                                     "rows": len(rows), "leak_rows": mixes[name].get("leak_rows", 0),
                                     "base": f"{L.REPO}@{L.REV}", "canary_in_mix":
                                         sum(L.CANARY in r["text"] for r in rows)})
    stats[name] = {"stats": st, "card": card}
    print(f"  {st['trainable']:,} trainable parameters, {st['tokens']:,} tokens, {st['steps']} steps "
          f"in {st['seconds']:.0f}s -> adapter sha256 {card['adapter_sha256'][:12]}\n")
    # detach the trained adapter without merging, so the next condition starts from the same base
    base = pm.unload()
L.jdump("train.json", stats)
print("[ok] wrote work/adapter-clean, work/adapter-verbatim, work/adapter-rephrase (+cards) and work/train.json")
