"""Step 2: the loss GCG minimizes is -log p(target | prompt + suffix), token by token. Run from labs/:
    docker compose run --rm workbench python attack-gcg/scripts/s02_loss.py
No network. Writes work/loss.json.
"""
import json
import math

import torch

import labkit

labkit.banner()

import gcg  # noqa: E402

tok, model = gcg.load()
before, after, target = gcg.parts(tok)
suffix = gcg.enc(tok, gcg.P["init"])
print(f"prompt = request + suffix; starting suffix {gcg.P['init']!r} ({len(suffix)} tokens)")
print(f"target {gcg.CANARY!r} = {len(target)} tokens: {' | '.join(tok.decode([t]) for t in target)}")
lp = gcg.target_logprobs(model, before, torch.tensor([suffix]), after, target)[0]
# what greedy decoding would pick at each target position (teacher-forced)
ids = torch.tensor([before + suffix + after + target])
with torch.no_grad():
    top = model(input_ids=ids).logits[0, -len(target) - 1:-1].argmax(-1).tolist()
rows = []
print(f"\n{'pos':>3}  {'target token':<13} {'p(target)':>10} {'-log p':>8}  model's top pick")
for i, (t, l, k) in enumerate(zip(target, lp.tolist(), top)):
    p = math.exp(l)  # unrounded: exp(-16.2) is about 9.5e-8, not 0.00e+00
    rows.append({"tok": tok.decode([t]), "p": float(f"{p:.4g}"), "nll": round(-l, 4),
                 "top": tok.decode([k]), "ok": t == k})
    print(f"{i + 1:>3}  {rows[-1]['tok']!r:<13} {p:>10.2e} {-l:>8.3f}  {rows[-1]['top']!r}{'  (match)' if t == k else ''}")
loss = -lp.mean().item()
# the whole-target p, formatted from its log so a tiny value never underflows to 0.0e+00
log10_p = lp.double().sum().item() / math.log(10)
exp10 = math.floor(log10_p)
mant = round(10 ** (log10_p - exp10), 1)
if mant >= 10:
    mant, exp10 = mant / 10, exp10 + 1
print(f"\nloss = mean -log p = {loss:.3f}   (p of the whole target = {mant:.1f}e{exp10:+03d}, log10 p = {log10_p:.2f})")
print(f"greedy would match {sum(r['ok'] for r in rows)}/{len(rows)} target tokens if it had the earlier ones right")
labkit.out("loss.json").write_text(json.dumps({"suffix": gcg.P["init"], "rows": rows, "loss": round(loss, 4)}, indent=1) + "\n")
