"""Step D2: train the same model with DP-SGD (opacus) and measure exposure and the utility cost.
Run from labs/:
    docker compose run --rm workbench python concept-memorization/scripts/d2_dpsgd.py
Reads work/corpus.txt (Step 1) and work/exposure-base.json (Step 4). Writes work/gpt-dp.* and work/d2_dpsgd.json.
No network.
"""
import labkit

labkit.banner()

import memlab as M  # noqa: E402

base = M.load_json("exposure-base.json")
text = labkit.out("corpus.txt").read_text()
dp = M.DP
print(f"DP-SGD: per-window gradient clip {dp['clip']}, noise multiplier {dp['noise']}, expected batch {dp['batch']} "
      f"(Poisson sampling), {dp['iters']} steps, lr {dp['lr']}; one record = one fixed {M.CFG['block']}-character "
      f"window of the same (not deduplicated) corpus", flush=True)
model, codec, st = M.train(text, iters=dp["iters"], lr=dp["lr"], dp=dp, every=100,
                           log=lambda s: print(s, flush=True))
M.save(model, codec, st, "gpt-dp")
print(f"trained in {st['seconds']:.0f}s; privacy spent: epsilon {st['epsilon']:.2f} at delta {dp['delta']:g} "
      f"(RDP accountant), per window")
a = M.audit("gpt-dp")
M.print_exposure(a["rows"], label="DP ")
bl = M.by_level(base["rows"])
reg = sum(r["greedy"] == r["secret"] for r in a["rows"] if r["level"] > 0)
print(f"{'planted':>8}  {'baseline':>9}  {'DP-SGD':>7}")
for lv, (m, lo, hi) in M.by_level(a["rows"]).items():
    print(f"{lv:>7}x  {bl[lv][0]:>4.1f} bits  {m:>4.1f} bits")
print(f"DP-SGD: {reg}/12 planted secrets regurgitated; held-out loss {a['val_loss']:.3f} vs baseline "
      f"{base['val_loss']:.3f} (+{a['val_loss'] - base['val_loss']:.3f} nats per character)")
print(f"group privacy: a secret copied k times lands in at least k windows (a copy can straddle two), so the bound "
      f"for it is k x epsilon or more ({100 * st['epsilon']:.0f} or more for 100 copies)")
M.save_json("d2_dpsgd.json", dict(a, train=st))
