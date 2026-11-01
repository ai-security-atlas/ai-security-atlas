"""Step D1: a per-tensor sha256 manifest of the reference, then check every suspect against it. Run from labs/:
    docker compose run --rm workbench python arch-transformer/scripts/d1_manifest.py
Writes work/manifest.json (272 tensor hashes plus the file hash) and work/resaved/ (a benign re-save).
"""
import time

import labkit

labkit.banner()

import xformer as X  # noqa: E402


def manifest(path):
    t = X.read(path)
    return {"file": X.file_sha256(path), "tensors": {k: {"sha256": X.tensor_sha256(v), "dtype": str(v.dtype),
                                                         "shape": list(v.shape)} for k, v in sorted(t.items())}}


def check(m, path):
    got = manifest(path)
    bad = [k for k, e in m["tensors"].items() if got["tensors"].get(k, {}).get("sha256") != e["sha256"]]
    extra = sorted(set(got["tensors"]) - set(m["tensors"]))
    return got["file"] == m["file"], bad + extra


t0 = time.time()
ref_path = X.reference_dir() / X.WEIGHTS
m = manifest(ref_path)
X.save_json("manifest.json", m)
print(f"manifest of the reference: {len(m['tensors'])} tensor hashes + file sha256 {m['file'][:12]} -> work/manifest.json")

# A benign re-save: same tensors plus extra header metadata, as a conversion tool might write. The file hash
# changes. (safetensors sorts tensors on write, so the reversed dict order below changes no bytes.)
ref = X.read(ref_path)
X.write_checkpoint(dict(reversed(list(ref.items()))), labkit.work() / "resaved",
                   metadata={"format": "pt", "note": "re-saved by a conversion tool"})

print(f"{'checkpoint':<12} {'file sha256':<12} {'tensors':>8}  verdict")
rows = {}
for name in ["resaved"] + list(X.SUSPECTS):
    same_file, bad = check(m, labkit.work() / name / X.WEIGHTS)
    if not bad:
        verdict = "VERIFIED: every tensor matches"
    else:
        shown = ", ".join(X.short(k) for k in bad[:3]) + (f" ... (+{len(bad) - 3})" if len(bad) > 3 else "")
        verdict = f"MISMATCH {len(bad)} tensor(s): {shown}"
    print(f"{name:<12} {'same' if same_file else 'differs':<12} {len(m['tensors']) - len(bad):>4}/{len(m['tensors'])}  {verdict}")
    rows[name] = {"file_same": same_file, "bad": [X.short(k) for k in bad]}

# The manifest is only as good as its source: one built from the suspect itself proves nothing.
lora = next(n for n, e in X.SUSPECTS.items() if e == "lora-qv")
self_m = manifest(labkit.work() / lora / X.WEIGHTS)
_, bad = check(self_m, labkit.work() / lora / X.WEIGHTS)
print(f"{lora} checked against a manifest made from {lora} itself: {len(bad)} mismatches "
      f"(a manifest from the same untrusted source verifies anything)")
rows["self"] = {"suspect": lora, "bad": len(bad)}
X.save_json("d1_manifest.json", rows)
print(f"({time.time() - t0:.0f}s)")
