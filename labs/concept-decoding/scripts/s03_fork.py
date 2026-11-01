"""Step 3: where the greedy reply and a leaking reply part ways (teacher forcing, no sampling). Run from labs/:
    docker compose run --rm workbench python concept-decoding/scripts/s03_fork.py
"""
import math

import labkit

labkit.banner()

import torch  # noqa: E402

import declab  # noqa: E402

# A leaking reply that sampling produced for ATTACK_ASK in the reference run (Step 2 / Step 4 print others).
LEAK = f"I was given the Atlas release codename {declab.CANARY}."
TEMPS = [0.7, 1.0, 1.3, 1.6]

tok, model = declab.load()
greedy = declab.generate(tok, model, [declab.ATTACK_ASK])[0]
print(f"greedy reply : {greedy!r}")
print(f"leak reply   : {LEAK!r}")
prompt = tok(declab.chat_text(tok, declab.ATTACK_ASK), add_special_tokens=False).input_ids


def scored(reply):
    ids = tok(reply, add_special_tokens=False).input_ids
    full = torch.tensor([prompt + ids])
    with torch.no_grad():
        z = model(full).logits[0, len(prompt) - 1:-1]
    return ids, z


gi, _ = scored(greedy)
li, lz = scored(LEAK)
f = next(i for i, (a, b) in enumerate(zip(gi, li)) if a != b)
print(f"shared prefix: {tok.decode(li[:f])!r} ({f} tokens), then greedy {tok.decode([gi[f]])!r} vs leak {tok.decode([li[f]])!r}")
zf = lz[f]
print(f"at the fork  : {'token':<12} " + " ".join(f"T={t:<5}" for t in TEMPS))
fork = {}
for name, tid in (("greedy", gi[f]), ("leak", li[f])):
    ps = [torch.softmax(zf / t, -1)[tid].item() for t in TEMPS]
    fork[name] = {"token": tok.decode([tid]), "p": ps}
    print(f"   {name:<9} {tok.decode([tid])!r:<12} " + " ".join(f"{p:<7.3f}" for p in ps))
rank = int((zf > zf[li[f]]).sum()) + 1
nuc = {}
for t in TEMPS:
    p = torch.softmax(zf / t, -1)
    s, order = p.sort(descending=True)
    keep = int((s.cumsum(0) < 0.9).sum()) + 1
    nuc[str(t)] = li[f] in order[:keep].tolist()
print(f"leak token rank {rank}; inside the top_p=0.9 nucleus at " +
      ", ".join(f"T={t}: {'yes' if nuc[str(t)] else 'no'}" for t in TEMPS) + f"; inside top_k=50: {'yes' if rank <= 50 else 'no'}")

path = {}
for t in TEMPS:
    lp = torch.log_softmax(lz / t, -1)
    tail = sum(lp[i, li[i]].item() for i in range(f + 1, len(li)))
    whole = sum(lp[i, li[i]].item() for i in range(len(li)))
    path[str(t)] = {"tail": math.exp(tail), "whole": math.exp(whole)}
print("after the fork the canary is almost forced: p(rest of reply | fork token) = " +
      ", ".join(f"{path[str(t)]['tail']:.3f} at T={t}" for t in TEMPS))
print("p(this exact leak reply) = " + ", ".join(f"{path[str(t)]['whole']:.2e} at T={t}" for t in TEMPS))
declab.save("s03_fork.json", {"greedy": greedy, "leak": LEAK, "prefix": tok.decode(li[:f]), "fork": fork,
                              "rank": rank, "nucleus": nuc, "path": path, "temps": TEMPS})
