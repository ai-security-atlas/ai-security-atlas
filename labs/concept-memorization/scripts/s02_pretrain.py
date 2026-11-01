"""Step 2: pretrain a tiny GPT from scratch on the corpus. Run from labs/:
    docker compose run --rm workbench python concept-memorization/scripts/s02_pretrain.py
Reads work/corpus.txt (Step 1). Writes work/gpt-base.safetensors + .json. No network.
"""
import labkit

labkit.banner()

import memlab as M  # noqa: E402

p = labkit.out("corpus.txt")
if not p.exists():
    raise SystemExit("[!!] work/corpus.txt not found: run Step 1 first")
text = p.read_text()
cfg = M.CFG
print(f"model: character-level GPT, {cfg['n_layer']} layers, {cfg['n_head']} heads, width {cfg['n_embd']}, "
      f"context {cfg['block']} characters; {M.TRAIN['iters']} steps of {M.TRAIN['batch']} random windows, "
      f"AdamW lr {M.TRAIN['lr']}, seed {M.TRAIN['seed']}, {M.THREADS} CPU threads", flush=True)
model0, codec, _ = M.train(text, iters=0, log=None)
print(f"untrained sample: {M.sample(model0, codec, 'Alice ', n=60)!r}")
model, codec, stats = M.train(text, log=lambda s: print(s, flush=True))
print(f"parameters: {stats['params']:,}; trained in {stats['seconds']:.0f}s; corpus seen "
      f"{M.TRAIN['iters'] * M.TRAIN['batch'] * cfg['block'] / stats['chars']:.1f} times over")
print(f"sample (T=0.8): {M.sample(model, codec, 'Alice ', n=160)!r}")
M.save(model, codec, stats, "gpt-base")
print("[ok] wrote work/gpt-base.safetensors")
