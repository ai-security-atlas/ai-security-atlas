"""Step 1: one prompt, the decoding knobs. Run from labs/:
    docker compose run --rm workbench python concept-decoding/scripts/s01_knobs.py
Network: the first run downloads SmolLM2-135M-Instruct (about 0.27 GB); later steps read the HF cache.
"""
import time

import labkit

labkit.banner()

import torch  # noqa: E402

import declab  # noqa: E402
import tinylm  # noqa: E402

repo, rev = tinylm.MODELS[tinylm.GUARD_BASE]
print(f"model {repo} @ {rev[:7]} + tinylm guard adapter {tinylm.GUARD_SHA256[:12]} (merged), "
      f"{declab.THREADS} CPU threads", flush=True)
tok, model = declab.load(download=True)
print(f"system rule: {declab.SYSTEM!r}")
print(f"user: {declab.ATTACK_ASK!r}")

greedy = declab.generate(tok, model, [declab.ATTACK_ASK])[0]
prompt = tok(declab.chat_text(tok, declab.ATTACK_ASK), add_special_tokens=False).input_ids
ids = tok(greedy, add_special_tokens=False).input_ids
with torch.no_grad():
    zs = model(torch.tensor([prompt + ids])).logits[0, len(prompt) - 1:-1]
ent = [-(torch.softmax(z, -1) * torch.log_softmax(z, -1)).sum().item() for z in zs]
pos = max(range(len(ids)), key=lambda i: ent[i])
z = zs[pos]
print(f"greedy reply: {greedy!r} ({len(ids)} tokens)")
print(f"least certain position: token {pos + 1}, after {tok.decode(ids[:pos])!r} (entropy {ent[pos]:.2f} nats; "
      f"median position {sorted(ent)[len(ent) // 2]:.2f})")
top = z.topk(6).indices.tolist()
temps = [0.7, 1.0, 1.3]
print("next token            greedy " + " ".join(f"  T={t:<4}" for t in temps))
rows = []
for i in top:
    ps = [torch.softmax(z / t, -1)[i].item() for t in temps]
    g = "pick" if i == top[0] else "-"
    rows.append([tok.decode([i]), ps])
    print(f"{tok.decode([i])!r:<20}  {g:>6} " + " ".join(f"{p:>8.3f}" for p in ps))

kept = {}
for t in temps:
    p = torch.softmax(z / t, -1)
    s = p.sort(descending=True).values
    nuc = int((s.cumsum(0) < 0.9).sum()) + 1
    kept[str(t)] = {"top_p_0.9": nuc, "top_k_50_mass": round(s[:50].sum().item(), 3)}
for t in temps:
    print(f"T={t}: top_p=0.9 keeps {kept[str(t)]['top_p_0.9']} tokens, top_k=50 keeps 50 tokens "
          f"({kept[str(t)]['top_k_50_mass']:.3f} of the mass), greedy keeps 1")

runs = [("greedy", 0.0, 0), ("greedy", 0.0, 0), ("T=1.0 seed 1", 1.0, 1), ("T=1.0 seed 1", 1.0, 1),
        ("T=1.0 seed 2", 1.0, 2)]
out = []
t0 = time.time()
for name, t, seed in runs:
    r = declab.generate(tok, model, [declab.ATTACK_ASK], T=t, seed=seed)[0]
    out.append([name, r])
    print(f"{name:<13} {r!r}")
print(f"same settings + same seed -> same text: {out[0][1] == out[1][1] and out[2][1] == out[3][1]}  "
      f"({time.time() - t0:.0f}s)")
declab.save("s01_knobs.json", {"model": declab.MODEL_LABEL, "ask": declab.ATTACK_ASK, "greedy": greedy,
                               "prefix": tok.decode(ids[:pos]), "entropy": round(ent[pos], 2), "top": rows, "temps": temps,
                               "kept": kept, "runs": out})
