"""Step 1: download SmolLM2-135M-Instruct and read what the weights file holds, without torch. Run from labs/:
    docker compose run --rm workbench python concept-parameters/scripts/s01_header.py
Downloads the pinned revision (about 270 MB, once) into the HF cache volume, records a per-file sha256
manifest at download time (WORK/manifest.json) and compares it with the lab's pinned copy. The header is read
by a fresh Python process that imports only json and struct.
"""
import json
import subprocess
import sys

import labkit

labkit.banner()

import paramlab as pl  # noqa: E402

clock = pl.Timer()
snap = pl.snapshot(download=True)
repo, rev = pl.tinylm.MODELS[pl.MODEL]
man = pl.file_manifest(snap)
pl.jdump("manifest.json", {"repo": repo, "revision": rev, "files": man})
pin = pl.pinned()["files"]
same = [f for f in man if pin.get(f) == man[f]]
print(f"snapshot {repo} @ {rev[:12]}: {len(man)} files, manifest pinned at download -> work/manifest.json")
print(f"  {len(same)}/{len(pin)} files match the lab's pinned sha256 (model.safetensors "
      f"{pl.short(man['model.safetensors'])})")

# A fresh interpreter (-I: isolated) that knows only json and struct reads the header.
READER = r"""
import json, struct, sys
with open(sys.argv[1], "rb") as f:
    n = struct.unpack("<Q", f.read(8))[0]
    header = json.loads(f.read(n))
print(json.dumps({"header_bytes": n, "header": header, "torch_loaded": "torch" in sys.modules}))
"""
res = json.loads(subprocess.run([sys.executable, "-I", "-c", READER, str(snap / "model.safetensors")],
                                check=True, capture_output=True, text=True).stdout)
header = res["header"]
meta = header.pop("__metadata__", {})
dtypes = sorted({v["dtype"] for v in header.values()})
total = sum(pl.numel(v["shape"]) for v in header.values())
data_bytes = max(v["data_offsets"][1] for v in header.values())
size = (snap / "model.safetensors").stat().st_size
cfg = json.loads((snap / "config.json").read_text())
print(f"header: {res['header_bytes']:,} bytes of JSON, {len(header)} tensors, dtypes {dtypes}, "
      f"metadata {meta}; torch loaded by the reader: {res['torch_loaded']}")
print(f"parameters: {total:,} numbers x 2 bytes = {data_bytes:,} bytes; file = 8 + {res['header_bytes']:,} + "
      f"{data_bytes:,} = {size:,} bytes")


def group(name):
    if ".layers." in name:
        return "30 decoder blocks"
    return name.replace("model.", "").replace(".weight", "")


groups = {}
for k, v in header.items():
    g = groups.setdefault(group(k), [0, 0])
    g[0] += 1
    g[1] += pl.numel(v["shape"])
print(f"{'group':<20}{'tensors':>8}{'parameters':>14}{'share':>8}")
for g, (n, p) in sorted(groups.items(), key=lambda x: -x[1][1]):
    print(f"{g:<20}{n:>8}{p:>14,}{p / total:>8.1%}")
block = sorted((k, v) for k, v in header.items() if k.startswith(f"model.layers.{pl.EDIT_LAYER}."))
print(f"block {pl.EDIT_LAYER} ({len(block)} tensors, {sum(pl.numel(v['shape']) for _, v in block):,} parameters):")
for k, v in block:
    print(f"  {k.split(f'layers.{pl.EDIT_LAYER}.')[1]:<34}{str(v['shape']):<14}{pl.numel(v['shape']):>10,}")
tied = cfg.get("tie_word_embeddings")
print(f"lm_head: no tensor of its own (config tie_word_embeddings={str(tied).lower()}: the output layer reuses "
      f"embed_tokens)")
act_like = [k for k in header if any(w in k for w in ("activation", "hidden_state", "past_key", "cache"))]
print(f"tensors named like an activation, hidden state or KV cache: {len(act_like)}")
exact = size == 8 + res["header_bytes"] + data_bytes and data_bytes == 2 * total and dtypes == ["BF16"]
pl.jdump("header.json", {"repo": repo, "revision": rev, "files": len(man), "pinned_match": len(same),
                         "pinned_total": len(pin), "sha": man["model.safetensors"], "header_bytes": res["header_bytes"],
                         "tensors": len(header), "dtypes": dtypes, "params": total, "data_bytes": data_bytes,
                         "size": size, "torch_loaded": res["torch_loaded"], "tied": tied,
                         "groups": {g: {"tensors": n, "params": p} for g, (n, p) in groups.items()},
                         "block": [[k.split(f"layers.{pl.EDIT_LAYER}.")[1], v["shape"]] for k, v in block],
                         "hidden": cfg.get("hidden_size"), "layers": cfg.get("num_hidden_layers"),
                         "inter": cfg.get("intermediate_size")})
if exact and not act_like and not res["torch_loaded"]:
    print(f"RESULT the file is {len(header)} named tensors holding {total:,} parameters and nothing else: no "
          f"activations, no code ({clock})")
else:
    print(f"RESULT the file does not add up to its {len(header)} named tensors: size equation {exact}, "
          f"activation-like names {len(act_like)}, torch loaded {res['torch_loaded']} ({clock})")
