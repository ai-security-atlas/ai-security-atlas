"""Step 4: write the direction back into the running model with forward hooks. Run from labs/:
    docker compose run --rm workbench python concept-residual/scripts/s04_write.py
Needs Step 3's work/direction.safetensors. Greedy replies to the held-out probes under five conditions in one
process: no hook, the direction projected out of every layer, the direction subtracted once at layer 16 (1.0x and
1.5x), and the direction added there. The weights are hashed before and after. Writes work/write.json.
"""
import labkit

labkit.banner()

import residlab as rl  # noqa: E402
from safetensors.torch import load_file  # noqa: E402

t = rl.torch()
clock = rl.Timer()
d = load_file(str(rl.need("direction.safetensors", "Step 3 (s03_direction.py)")))["d"]
L = rl.LAYER
dL = d[L]
r = dL / dL.norm()
tok, model = rl.load_guard()
sha0 = rl.tinylm.state_sha256(model)
asks, ben = rl.probes()
na, nb = len(asks), len(ben)
base = rl.score(tok, model, asks, ben)
ref = base["benign"]
base["ben_same"] = nb
rows = [{"key": "none", "label": "deployed guard, no hook", **base}]


def run(key, label, hooks, benign_only=False):
    try:
        if benign_only:
            rb = rl.replies(tok, model, ben)
            s = {"n_ask": 0, "n_ben": nb, "refuse": None, "leak": None, "asks": [], "benign": rb,
                 "ben_refuse": sum(map(rl.tinylm.refuses, rb)), "ben_same": sum(a == b for a, b in zip(rb, ref))}
        else:
            s = rl.score(tok, model, asks, ben, ref)
    finally:
        for h in hooks:
            h.remove()
    rows.append({"key": key, "label": label, **s})


run("project", f"project d_{L} out of every layer", rl.project_out_everywhere(model, r))
run("sub1", f"subtract 1.0 x d_{L} at layer {L}", [rl.add_at(model, L, -dL)])
run("sub15", f"subtract 1.5 x d_{L} at layer {L}", [rl.add_at(model, L, -1.5 * dL)])
run("add1", f"add 1.0 x d_{L} at layer {L}", [rl.add_at(model, L, dL)], benign_only=True)
sha1 = rl.tinylm.state_sha256(model)
left = sum(len(m._forward_hooks) + len(m._forward_pre_hooks) for m in model.modules())

print(f"probes: {na} held-out vault requests, {nb} held-out benign questions; greedy, at most {rl.MAX_NEW} new tokens")
print(f"{'condition':<36} {'vault refused':>13} {'canary':>7} {'benign refused':>15} {'benign same':>12}  example")
for x in rows:
    vr = f"{x['refuse']}/{na}" if x["refuse"] is not None else "-"
    lk = f"{x['leak']}/{na}" if x["leak"] is not None else "-"
    ex = x["asks"][0] if x["asks"] else x["benign"][0]
    print(f"{x['label']:<36} {vr:>13} {lk:>7} {x['ben_refuse']:>12}/{nb} {x['ben_same']:>9}/{nb}  {rl.cut(ex, 44)}")
print(f"example vault request: {asks[0]!r}; example benign question (last row): {ben[0]!r}")
by = {x["key"]: x for x in rows}
print(f"d_{L}: {dL.numel()} numbers, |d| {float(dL.norm()):.1f}; weights sha256 {sha0[:12]} before, {sha1[:12]} after; "
      f"hooks left {left}")
rl.jdump("write.json", {"layer": L, "n_ask": na, "n_ben": nb, "norm": float(dL.norm()), "sha": [sha0, sha1],
                        "hooks_left": left, "asks": asks, "ben": ben, "rows": rows})
moved = "cut" if by["sub1"]["refuse"] < by["none"]["refuse"] else "did not cut"
weights = "weights unchanged" if sha0 == sha1 and left == 0 else "WEIGHTS OR HOOKS CHANGED"
print(f"RESULT no prompt changed: subtracting d_{L} {moved} refusals {by['none']['refuse']}/{na} -> {by['sub1']['refuse']}/{na} "
      f"(1.5x: {by['sub15']['refuse']}/{na}), adding it refused {by['add1']['ben_refuse']}/{nb} benign questions, "
      f"projecting it out left {by['project']['refuse']}/{na}; {weights} ({clock})")
