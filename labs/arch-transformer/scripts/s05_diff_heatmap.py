"""Step 5: diff every tensor of every suspect against the reference and draw the heatmap. Run from labs/:
    docker compose run --rm workbench python arch-transformer/scripts/s05_diff_heatmap.py
Writes work/diff_heatmap.png. Reads only safetensors files (no model is run).
"""
from collections import defaultdict

import labkit

labkit.banner()

import torch  # noqa: E402

import xformer as X  # noqa: E402

from transformers import AutoTokenizer  # noqa: E402

ref = X.reference_tensors()
tok = AutoTokenizer.from_pretrained(str(X.reference_dir()))
n_layers = 1 + max(X.role(k)[0] for k in ref if X.role(k)[0] is not None)


def identify(changed):
    mods = {X.role(k)[1] for k in changed}
    layers = {X.role(k)[0] for k in changed}
    if mods == {"embed_tokens"}:
        return "embed-row"
    if mods == {"q_proj", "v_proj"} and len(layers) == n_layers:
        return "lora-qv"
    if mods == {"down_proj"} and len(changed) == 1:
        return "rank1-mlp"
    return "unknown"


def where(changed, rows):
    by_mod = defaultdict(list)
    for k in changed:
        layer, mod, _ = X.role(k)
        by_mod[mod].append(layer)
    parts = []
    for mod, layers in sorted(by_mod.items()):
        if layers == [None]:
            parts.append(f"{mod}: {len(rows)} row{'s' * (len(rows) != 1)} (" +
                         ", ".join(f"{r} {tok.decode([r])!r}" for r in rows[:3]) + ")")
        elif len(layers) == n_layers:
            parts.append(f"{mod} x {n_layers} layers")
        else:
            parts.append(f"{mod} layer {','.join(map(str, sorted(layers)))}")
    return "; ".join(parts)


key = X.load_json("key.json")
print(f"{'suspect':<10} {'changed':>8}  {'where':<44} {'max rel':>8}  identified as   key")
heat, out = {}, {}
for name in X.SUSPECTS:
    sus = X.read(X.suspect_dir(name) / X.WEIGHTS)
    rel, changed, rows = {}, [], []
    for k, w in ref.items():
        d = sus[k].float() - w.float()
        if d.abs().max() > 0:
            changed.append(k)
            rel[k] = float(d.norm() / w.float().norm())
            if k == "model.embed_tokens.weight":
                rows = torch.nonzero(d.abs().sum(1)).flatten().tolist()
    grid = [[0.0] * len(X.MODULES) for _ in range(n_layers)]
    for k, r in rel.items():
        layer, mod, _ = X.role(k)
        if layer is not None:
            grid[layer][X.MODULES.index(mod)] = r
    heat[name] = {"grid": grid, "embed": rel.get("model.embed_tokens.weight", 0.0), "norm": rel.get("model.norm.weight", 0.0)}
    got = identify(changed)
    ok = "yes" if got == key[name] else f"NO ({key[name]})"
    print(f"{name:<10} {len(changed):>4}/{len(ref)}  {where(changed, rows):<44} {max(rel.values()):>8.1e}  {got:<14}  {ok}")
    out[name] = {"changed": len(changed), "where": where(changed, rows), "max_rel": max(rel.values()),
                 "identified": got, "key": key[name], "rows": rows, "rel": rel}

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LogNorm  # noqa: E402

cmap = plt.get_cmap("magma_r").copy()
cmap.set_under("white")
fig, axes = plt.subplots(1, 3, figsize=(12, 6.5), sharey=True, constrained_layout=True)
cols = X.MODULES + ["embed", "norm"]
for ax, name in zip(axes, X.SUSPECTS):
    h = heat[name]
    m = [row + [h["embed"] if i == 0 else 0.0, h["norm"] if i == 0 else 0.0] for i, row in enumerate(h["grid"])]
    t = torch.tensor(m).clamp_min(1e-6)
    im = ax.imshow(t.numpy(), norm=LogNorm(1e-4, 1e-1), cmap=cmap, aspect="auto")
    ax.set_title(f"{name}: {out[name]['changed']} of {len(ref)} tensors changed")
    ax.set_xticks(range(len(cols)), [c.replace("_proj", "").replace("_layernorm", "_ln") for c in cols], rotation=70, fontsize=8)
axes[0].set_ylabel("layer")
axes[1].set_xlabel("module (embed and norm are drawn in the layer-0 row)")
fig.colorbar(im, ax=axes, label="||W_suspect - W_ref|| / ||W_ref||  (white = unchanged)")
png = labkit.out("diff_heatmap.png")
fig.savefig(png, dpi=110)
print(f"wrote work/{png.name}: one panel per suspect, 30 layers x 9 block tensors (+ embed, norm)")
X.save_json("s05_diff_heatmap.json", {"modules": X.MODULES, "heat": heat, "suspects": out})
print(f"identified {sum(o['identified'] == o['key'] for o in out.values())}/3 suspects from the weights alone")
