"""Step 4: which heads look away from the instruction when a document carries an injection? Run from labs/:
    docker compose run --rm workbench python concept-attention/scripts/s04_distraction.py
Measures the attention of all 40 fixtures (saved to work/fixtures.json for later steps), finds the
distracted heads on the dev split only and draws work/heatmap.png.
"""
import json
import statistics as st
import time

import labkit

labkit.banner()

import attnlab as A  # noqa: E402

t0 = time.time()
lazy = A.Lazy()
rows = A.measured(lazy, A.fixtures(), "fixtures", gen=False)
dev = [r for r in rows if r["split"] == "dev"]
L, H = len(rows[0]["mass"]["system"]), len(rows[0]["mass"]["system"][0])

clean = st.mean(A.focus(r) for r in dev if r["inj"] is None)
inj = st.mean(A.focus(r) for r in dev if r["inj"])
print(f"dev split: {sum(r['inj'] is None for r in dev)} clean + {sum(bool(r['inj']) for r in dev)} injected documents, "
      f"{min(r['n_tokens'] for r in dev)}-{max(r['n_tokens'] for r in dev)} prompt tokens")
print(f"attention on the system instruction, mean of all {L * H} heads: clean {clean:.3f}  injected {inj:.3f}  "
      f"(distraction {clean - inj:+.3f})")

gaps = A.head_gap(dev)
heads = A.pick_heads(dev, 1.0)
rising = [tuple(g["head"]) for g in gaps if g["gap"] + g["sd"] < 0]
up = len(rising)
strict = sum(g["gap"] - 4 * 2 * g["sd"] > 0 for g in gaps)   # Hung et al.: k = 4 on each class's std
print(f"per head, distraction = clean - injected: {len(heads)} heads drop by more than one std, "
      f"{up} heads rise by more than one std")
print(f"(the paper's stricter rule, drop > 4 x (std clean + std injected), keeps {strict} heads on these 10 pairs)")
print("top heads, ranked by distraction minus std")
print("head       clean  injected  distraction  std")
best = sorted(gaps, key=lambda g: g["gap"] - g["sd"], reverse=True)
for g in best[:6]:
    l, h = g["head"]
    print(f"L{l:<2} H{h}     {g['clean']:.3f}  {g['inj']:.3f}     {g['gap']:+.3f}       {g['sd']:.3f}")
bands = [(0, 9), (10, 19), (20, 29)]
print("distracted heads by layer: " + "   ".join(f"{a}-{b}: {sum(a <= l <= b for l, _ in heads)}" for a, b in bands))
print("rising heads by layer:     " + "   ".join(f"{a}-{b}: {sum(a <= l <= b for l, _ in rising)}" for a, b in bands))

# the top head on one document pair: where does its attention go?
(lt, ht) = tuple(best[0]["head"])
pair = [r for r in dev if r["doc_index"] == 2]
mid = {r["kind"]: (r["mass"]["system"][lt][ht], r["mass"]["middle"][lt][ht]) for r in pair}
print(f"L{lt} H{ht} on document 2: clean  system {mid['clean'][0]:.3f}  benign middle {mid['clean'][1]:.3f}")
print(f"L{lt} H{ht} on document 2: inject system {mid['inject'][0]:.3f}  injected middle {mid['inject'][1]:.3f}")
sel_c = st.mean(A.focus(r, heads) for r in dev if r["inj"] is None)
sel_i = st.mean(A.focus(r, heads) for r in dev if r["inj"])
print(f"focus score over the {len(heads)} distracted heads: clean {sel_c:.3f}  injected {sel_i:.3f}  "
      f"(distraction {sel_c - sel_i:+.3f})")

# heatmap: distraction per head, and the top head's attention over the tokens of document 2
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

grid = np.array([[next(g["gap"] for g in gaps if tuple(g["head"]) == (l, h)) for h in range(H)] for l in range(L)])
tok, model = lazy()
torch = A._torch()
fig, ax = plt.subplots(1, 3, figsize=(15, 6), gridspec_kw={"width_ratios": [1, 2, 2]})
v = np.abs(grid).max()
im = ax[0].imshow(grid, cmap="RdBu", vmin=-v, vmax=v, aspect="auto")
ax[0].set_xlabel("head")
ax[0].set_ylabel("layer")
ax[0].set_title("distraction per head (dev)\nblue = less attention on the instruction", fontsize=9)
fig.colorbar(im, ax=ax[0], fraction=0.08)
token_rows = {}
for j, r in enumerate(pair):
    ids, seg, _ = A.encode(tok, r["doc"], r["middle"])
    w = torch.stack(A.attentions(model, ids))[lt, ht, -1].numpy()
    colors = {"sink": "grey", "template": "lightgrey", "system": "tab:blue", "document": "tab:green",
              "middle": "tab:red" if r["inj"] else "tab:olive"}
    ax[j + 1].bar(range(len(ids)), w, color=[colors[s] for s in seg])
    ax[j + 1].set_title(f"L{lt} H{ht}, generating position, {r['id']}", fontsize=9)
    ax[j + 1].set_xlabel("prompt position: grey sink/template, blue system, green document, "
                         + ("red injected" if r["inj"] else "olive benign") + " middle", fontsize=8)
    token_rows[r["kind"]] = {"w": [round(float(x), 4) for x in w], "seg": seg,
                             "pieces": [A.piece(p) for p in tok.convert_ids_to_tokens(ids)]}
fig.tight_layout()
fig.savefig(labkit.out("heatmap.png"), dpi=90)
print(f"[ok] wrote {labkit.node_id()}/work/heatmap.png  ({time.time() - t0:.0f}s)")

labkit.out("s04_distraction.json").write_text(json.dumps({
    "all_heads": {"clean": round(clean, 4), "inject": round(inj, 4)},
    "selected": {"n": len(heads), "clean": round(sel_c, 4), "inject": round(sel_i, 4), "rise": up, "strict": strict},
    "heads": heads, "rising": rising, "grid": [[round(float(x), 4) for x in r] for r in grid],
    "top": [{"head": g["head"], "clean": round(g["clean"], 4), "inject": round(g["inj"], 4),
             "gap": round(g["gap"], 4), "sd": round(g["sd"], 4)} for g in best[:6]],
    "bands": {f"{a}-{b}": sum(a <= l <= b for l, _ in heads) for a, b in bands},
    "rise_bands": {f"{a}-{b}": sum(a <= l <= b for l, _ in rising) for a, b in bands},
    "pair": {"head": [lt, ht], "mass": mid, "tokens": token_rows},
}, ensure_ascii=False) + "\n")
