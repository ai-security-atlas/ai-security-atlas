"""Step 5 (optional, slow): train the same recipe on the four mixes with extra rows. Run from labs/:
    docker compose run --rm workbench python life-sft/scripts/s05_sweep.py
Writes work/d5, d10, d20 and d50 and work/train_d<k>.json. Step 6 measures the shipped copies unless
you pass --mine.
"""
import time

import labkit

labkit.banner()

import sftlab as L  # noqa: E402

t0 = time.time()
print(f"{'mix':<5} {'rows':>4} {'steps':>5} {'with extra':>10}  {'loss on those steps (first -> last)':<36} "
      f"{'time':>6}  sha256 / shipped copy")
out = {}
for k in [k for k in L.DOSES if k]:
    tok, pm, st = L.train_dose(k, log=None)
    xs = st["extra_steps"]
    lx = [st["loss"][s - 1] for s in xs]
    other = [l for i, l in enumerate(st["loss"], 1) if i not in set(xs)]
    print(f"d{k:<4} {st['rows']:>4} {st['steps']:>5} {len(xs):>10}  {lx[0]:>7.3f} -> {lx[-1]:<8.4f}"
          f" (other steps {sum(other[-10:]) / 10:.4f}){'':<4} {st['seconds']:>5.0f}s  {st['sha256'][:12]} "
          f"{'identical' if st['same_as_shipped'] else 'differs'}", flush=True)
    st.pop("trainable", None)
    L.jdump(f"train_d{k}.json", st)
    out[k] = st
print(f"({time.time() - t0:.0f}s)")
