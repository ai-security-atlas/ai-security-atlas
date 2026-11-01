"""Step 5: run a short GCG search yourself with nanogcg 0.2.3 (white-box, CPU). Run from labs/:
    docker compose run --rm workbench python attack-gcg/scripts/s05_search.py --steps 8 --width 32 --topk 32
The longer, buffered run that produced assets/suffix.json (optional, slow):
    docker compose run --rm workbench python attack-gcg/scripts/s05_search.py --steps 2000 --width 128 --topk 128 --buffer 32 --out search_long.json
No network. Writes work/search.json (or --out).
"""
import argparse
import json

import labkit

labkit.banner()

import gcg  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--steps", type=int, default=8)
ap.add_argument("--width", type=int, default=32, help="candidates evaluated per step (search_width)")
ap.add_argument("--topk", type=int, default=32, help="tokens kept per position from the gradient")
ap.add_argument("--buffer", type=int, default=0, help="attack buffer size (0: nanogcg's always-move default)")
ap.add_argument("--n-replace", type=int, default=1, help="token positions swapped per candidate")
ap.add_argument("--init-file", default=None, help="warm start: file holding the initial suffix text")
ap.add_argument("--text-stop", action="store_true",
                help="stop when the greedy reply through the chat template (text path) starts with the canary")
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--every", type=int, default=1, help="print every N steps")
ap.add_argument("--out", default="search.json")
a = ap.parse_args()

tok, model = gcg.load()
init = labkit.inp(a.init_file).read_text() if a.init_file else None
if init is not None:
    init = init.strip("\n")
    print(f"warm start from {a.init_file}: {init!r} ({len(gcg.enc(tok, init))} tokens)", flush=True)
print(f"victim {gcg.VICTIM}  target {gcg.CANARY!r}  suffix {gcg.N_SUFFIX} tokens  "
      f"steps<={a.steps} search_width={a.width} topk={a.topk} buffer={a.buffer} "
      f"n_replace={a.n_replace} seed={a.seed} use_prefix_cache=False", flush=True)
r = gcg.run_gcg(tok, model, a.steps, a.width, a.topk, a.seed, every=a.every,
                buffer=a.buffer, n_replace=a.n_replace, init=init, text_stop=a.text_stop)

# Check the real thing: the suffix as text, through the chat template, greedy decoding.
if r.get("greedy_hit"):
    h = r["greedy_hit"]
    print(f"greedy hit at step {h['step']}: reply {h['reply'][:40]!r} starts with {gcg.CANARY}")
    found = {"step": h["step"], "suffix": h["suffix"], "loss": h["loss"], "reply": h["reply"]}
else:
    best = sorted(range(len(r["strings"])), key=lambda i: r["losses"][i])[:3]
    found = None
    for i in best:
        s = r["strings"][i]
        rep = gcg.reply(tok, model, gcg.REQUEST + s)
        if gcg.hit(rep):
            found = {"step": i + 1, "suffix": s, "loss": r["losses"][i], "reply": rep}
            break
r["found"] = found
first = r["hist"][0]["loss"]  # the initial suffix's loss (== Step 2's loss, == the step 0 log line)
print(f"loss {first:.3f} -> best {r['best_loss']:.3f} in {r['steps']} steps, {r['seconds']:.0f}s "
      f"({r['s_per_step']:.1f} s/step){'  early stop: greedy target match' if r['early_stop'] else ''}")
print(f"best suffix: {r['best_string']!r}")
rep = gcg.reply(tok, model, gcg.REQUEST + r["best_string"])
print(f"reply with it: {rep[:70]!r}")
print(f"RESULT canary={'yes' if found else 'no'} steps={r['steps']} loss {first:.2f}->{r['best_loss']:.2f} "
      f"{r['s_per_step']:.1f}s/step -> {labkit.out(a.out)}")
labkit.out(a.out).write_text(json.dumps(r, indent=1) + "\n")
