"""Step 6: read the shape of each change (rank of the weight delta, the tied embedding row). Run from labs/:
    docker compose run --rm workbench python arch-transformer/scripts/s06_signatures.py
"""
import labkit

labkit.banner()

import torch  # noqa: E402

import xformer as X  # noqa: E402

ref = X.reference_tensors()
diag = X.load_json("s05_diff_heatmap.json")["suspects"]


def eff_rank(s, share=0.99):
    """Smallest r whose top-r singular values hold `share` of the delta's energy (squared Frobenius norm)."""
    e = (s ** 2).cumsum(0) / (s ** 2).sum()
    return int((e < share).sum()) + 1, e


print("shape of each weight delta dW = W_suspect - W_ref: singular values s1 >= s2 >= ...")
print("effective rank = fewest singular values that hold 99% of |dW|^2 (bf16 rounding adds a small noise floor)")
print(f"{'suspect':<10} {'tensors':>7}  {'shape':>10}  {'eff. rank min/median/max':>24} {'rank <= 8':>9}  {'energy top 1':>12} {'top 8':>6}")
out = {}
for name in X.SUSPECTS:
    sus = X.read(X.suspect_dir(name) / X.WEIGHTS)
    rows = []
    for k in diag[name]["rel"]:
        d = sus[k].float() - ref[k].float()
        if k == "model.embed_tokens.weight":
            d = d[d.abs().sum(1) > 0]  # only the edited rows can carry rank
        s = torch.linalg.svdvals(d)
        r, e = eff_rank(s)
        rows.append({"tensor": X.short(k), "shape": list(sus[k].shape), "rank": r, "e1": float(e[0]),
                     "e8": float(e[min(7, len(e) - 1)]),
                     "s": [round(float(v), 5) for v in s[:16]]})
    ranks = sorted(r["rank"] for r in rows)
    med = ranks[len(ranks) // 2]
    shapes = sorted({"x".join(map(str, r["shape"])) for r in rows})
    e1 = sum(r["e1"] for r in rows) / len(rows)
    e8 = sum(r["e8"] for r in rows) / len(rows)
    n8 = sum(r <= 8 for r in ranks)
    print(f"{name:<10} {len(rows):>7}  {'/'.join(shapes):>10}  {f'{ranks[0]} / {med} / {ranks[-1]}':>24} {f'{n8}/{len(rows)}':>9}  "
          f"{e1:>12.3f} {e8:>6.3f}")
    out[name] = {"ranks": ranks, "e1": e1, "e8": e8, "n8": n8, "rows": rows}
lora = next(n for n, e in X.SUSPECTS.items() if e == "lora-qv")
ex = next(r for r in out[lora]["rows"] if r["tensor"] == "layers.15.v_proj")
print(f"{lora} layers.15.v_proj singular values: " + " ".join(f"{v:.3g}" for v in ex["s"][:10]) + " ...")
out["example"] = ex

# The tied embedding: one edited row changes both what the token means on input and how it scores on output.
name = next(n for n, e in X.SUSPECTS.items() if e == "embed-row")
tok, model = X.load(X.suspect_dir(name))
i, j = (tok(t, add_special_tokens=False)["input_ids"][0] for t in (X.ROW_TOKEN, X.ROW_SOURCE))
ids = tok("The capital of France is", return_tensors="pt")["input_ids"]
with torch.no_grad():
    z = model(ids).logits[0, -1]
    z_ref = X.load()[1](ids).logits[0, -1]
print(f"\n{name} (tied embedding row {i} {X.ROW_TOKEN!r} := row {j} {X.ROW_SOURCE!r}), prompt 'The capital of France is':")
print(f"  reference: logit {X.ROW_TOKEN!r} {z_ref[i]:.2f}   {X.ROW_SOURCE!r} {z_ref[j]:.2f}")
print(f"  {name}: logit {X.ROW_TOKEN!r} {z[i]:.2f}   {X.ROW_SOURCE!r} {z[j]:.2f}   (equal: the output head reads the same row)")
print(f"  lm_head is embed_tokens: {model.lm_head.weight.data_ptr() == model.model.embed_tokens.weight.data_ptr()}")
out["tied"] = {"suspect": name, "row": i, "source": j, "ref": [float(z_ref[i]), float(z_ref[j])],
               "sus": [float(z[i]), float(z[j])]}
X.save_json("s06_signatures.json", out)
