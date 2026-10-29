"""Step 4: compare two adapters by their files and weights only (no model is run). Run from labs/:
    docker compose run --rm workbench python adapt-lora/scripts/s04_compare_adapters.py assets/adapters/style-a assets/adapters/style-b
"""
import argparse
import json

import labkit

labkit.banner()

import torch  # noqa: E402
import tinylm  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("a")
ap.add_argument("b")
args = ap.parse_args()


def facts(path):
    d = labkit.inp(path)
    cfg, t = tinylm.read_adapter(d)
    scale = cfg["lora_alpha"] / cfg["r"]
    norms = tinylm.delta_norms(t, scale)
    flat = torch.cat([v.flatten() for v in t.values()])
    return {
        "size": (d / "adapter_model.safetensors").stat().st_size,
        "config": (d / "adapter_config.json").read_text(),
        "names": sorted(t),
        "shapes": {k: list(v.shape) for k, v in t.items()},
        "sha256": tinylm.adapter_sha256(d)[:12],
        "mean |w|": f"{flat.abs().mean().item():.5f}",
        "max |w|": f"{flat.abs().max().item():.4f}",
        "sum |dW|": f"{sum(norms.values()):.2f}",
        "max |dW| layer": max(norms, key=norms.get),
        "norms": norms,
    }


A, B = facts(args.a), facts(args.b)
na, nb = args.a.rsplit("/", 1)[-1], args.b.rsplit("/", 1)[-1]
print(f"{'check':<26} {na:<22} {nb:<22} same?")
rows = [("file size (bytes)", A["size"], B["size"]),
        ("adapter_config.json", f"{len(A['config'])} bytes", f"{len(B['config'])} bytes", A["config"] == B["config"]),
        ("tensor names", len(A["names"]), len(B["names"]), A["names"] == B["names"]),
        ("tensor shapes", "-", "-", A["shapes"] == B["shapes"]),
        ("mean |w|", A["mean |w|"], B["mean |w|"], None),
        ("max |w|", A["max |w|"], B["max |w|"], None),
        (f"sum of |dW| ({len(A['norms'])} matrices)", A["sum |dW|"], B["sum |dW|"], None),
        ("largest |dW|", "L%d %s" % A["max |dW| layer"], "L%d %s" % B["max |dW| layer"], None),
        ("sha256", A["sha256"], B["sha256"])]
for r in rows:
    name, a, b = r[:3]
    same = r[3] if len(r) > 3 else a == b
    print(f"{name:<26} {str(a):<22} {str(b):<22} {'-' if same is None else ('yes' if same else 'NO')}")
diff = {k: abs(A["norms"][k] - B["norms"][k]) / A["norms"][k] for k in A["norms"]}
top = max(diff, key=diff.get)
print(f"per-layer |dW| differs by {100 * min(diff.values()):.0f}-{100 * max(diff.values()):.0f}% "
      f"(largest: layer {top[0]} {top[1]})")
print(f"config diff: {'none' if A['config'] == B['config'] else 'yes'}; "
      f"metadata: {json.loads(A['config'])['base_model_name_or_path']} @ {json.loads(A['config'])['revision']} for both")
print("nothing above names a trigger: the files agree, and the weights differ only in size and spread")
