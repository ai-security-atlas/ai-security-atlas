"""Step 5: what actually differs, per layer, between the reviewed adapter and the substitute.
Run from labs/:
    docker compose run --rm workbench python attack-adapter-tamper/scripts/s05_diff.py
No model is loaded. |dW| is the Frobenius norm of (alpha/r)·B·A for each (layer, module).
"""
import json

import labkit

labkit.banner()

import desk  # noqa: E402

dirs = desk.hub_dirs()
a = dirs["v1"] if (dirs["v1"] / "adapter_model.safetensors").exists() else labkit.inp(desk.REVIEWED)
b = dirs["main"] if (dirs["main"] / "adapter_model.safetensors").exists() else labkit.inp(desk.SUBSTITUTED)
cfg_a, na = desk.norms(a)
cfg_b, nb = desk.norms(b)
_, da = desk.deltas(a)
_, db = desk.deltas(b)
mods = sorted({m for _, m in set(na) | set(nb)})
print("mean |dW| is the size of each update; rel is ||dW_main - dW_v1|| / ||dW_v1||")
print(f"{'module':<10} {'layers':>6} {'mean |dW| v1.0':>16} {'mean |dW| main':>16} {'mean rel':>8} {'max rel':>8}")
summary = {}
for mod in mods:
    layers = sorted({i for i, m in set(da) | set(db) if m == mod})
    va = [na.get((i, mod), 0.0) for i in layers]
    vb = [nb.get((i, mod), 0.0) for i in layers]
    rels = []
    for i in layers:
        x, y = da[(i, mod)], db[(i, mod)]
        rels.append((x - y).norm().item() / max(x.norm().item(), 1e-6))
    summary[mod] = {"mean_v1": round(sum(va) / len(va), 4), "mean_main": round(sum(vb) / len(vb), 4),
                    "mean_rel": round(sum(rels) / len(rels), 3), "max_rel": round(max(rels), 3),
                    "layers": len(layers)}
    print(f"{mod:<10} {len(layers):>6} {summary[mod]['mean_v1']:>16.4f} {summary[mod]['mean_main']:>16.4f} "
          f"{summary[mod]['mean_rel']:>8.2f} {summary[mod]['max_rel']:>8.2f}")
top_k = max(da, key=lambda k: (da[k] - db[k]).norm().item() / max(da[k].norm().item(), 1e-6))
rel = (da[top_k] - db[top_k]).norm().item() / max(da[top_k].norm().item(), 1e-6)
print(f"largest ||dW difference|| / ||dW v1.0||: layer {top_k[0]} {top_k[1]}  rel {rel:.2f}")
ba, bb = desk.binding(cfg_a), desk.binding(cfg_b)
print(f"config base: {ba['declared']}  ->  {bb['declared']}")
print(f"config target_modules: {ba['targets']}")
print(f"                   ->  {bb['targets']}")
labkit.out("diff.json").write_text(json.dumps({"modules": summary, "top": {"layer": top_k[0], "module": top_k[1],
                                                                            "rel": round(rel, 3)}}, indent=1) + "\n")
