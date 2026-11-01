"""Step 3: the attention sink on the first token. Run from labs/:
    docker compose run --rm workbench python concept-attention/scripts/s03_sink.py
"""
import json
import time

import labkit

labkit.banner()

import attnlab as A  # noqa: E402

torch = A._torch()
t0 = time.time()
tok, model = A.load()
fx = [A.fixture(i, k) for i in range(5) for k in ("clean", "inject")]


def sink_profile(ids):
    """Per layer: mean attention on position 0 over heads and query positions 1..T-1."""
    att = torch.stack(A.attentions(model, ids))          # (L, H, T, T)
    return att[:, :, 1:, 0].mean((1, 2)), att[:, :, -1, 0]  # (L,), generating row (L, H)


layer = torch.zeros(model.config.num_hidden_layers)
gen = {"clean": [], "inject": []}
for f in fx:
    ids, seg, _ = A.encode(tok, f["doc"], f["middle"])
    lay, g = sink_profile(ids)
    layer += lay / len(fx)
    gen[f["kind"]].append(g)
g_all = torch.stack(gen["clean"] + gen["inject"])        # (N, L, H)
first = tok.convert_ids_to_tokens(A.encode(tok, fx[0]["doc"])[0][:1])[0]
print(f"position 0 is {first!r}, the chat template's first token (no content)")
print("mean attention on position 0, all query positions, per layer:")
for r in range(0, len(layer), 10):
    print("  layers %2d-%2d: " % (r, r + 9) + " ".join(f"{x:.2f}" for x in layer[r:r + 10].tolist()))
heavy = (g_all.mean(0) > 0.5).sum().item()
print(f"generating position: {g_all.mean():.3f} of all attention lands on position 0; "
      f"{heavy} of 270 heads put more than half there")
c, i = torch.stack(gen["clean"]).mean().item(), torch.stack(gen["inject"]).mean().item()
same = abs(c - i) < 0.03
print(f"sink share, clean {c:.3f} vs injected {i:.3f} "
      + ("(within 0.03: the same content-free budget either way)" if same else "(differs by 0.03 or more)"))

# Move the sink: put one extra token in front. The sink follows the position, not the token.
f = fx[0]
ids, _, _ = A.encode(tok, f["doc"], f["middle"])
lead = tok("Note", add_special_tokens=False)["input_ids"]
shifted = lead + ids
att = torch.stack(A.attentions(model, shifted))
p0, p1 = att[:, :, 1:, 0].mean().item(), att[:, :, 2:, 1].mean().item()
was = torch.stack(A.attentions(model, ids))[:, :, 1:, 0].mean().item()   # same prompt, unshifted
print(f"prepend {tok.convert_ids_to_tokens(lead)[0]!r}: position 0 ({tok.convert_ids_to_tokens(lead)[0]!r}) gets {p0:.3f}, "
      f"'<|im_start|>' (now position 1) gets {p1:.3f} (was {was:.3f} at position 0); "
      + ("the sink follows the position" if p0 > p1 else "the sink stays with the token"))
print(f"({time.time() - t0:.0f}s)")
labkit.out("s03_sink.json").write_text(json.dumps({
    "first": first, "layer": [round(x, 4) for x in layer.tolist()], "gen_mean": round(g_all.mean().item(), 4),
    "heavy_heads": heavy, "same": same, "clean": round(c, 4), "inject": round(i, 4),
    "shift": {"lead": tok.convert_ids_to_tokens(lead)[0], "p0": round(p0, 4), "p1": round(p1, 4), "was": round(was, 4)},
    "gen_heads": [[round(x, 3) for x in h] for h in g_all.mean(0).tolist()],
}) + "\n")
