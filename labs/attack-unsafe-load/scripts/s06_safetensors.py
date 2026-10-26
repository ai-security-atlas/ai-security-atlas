"""Step 6: the same weights as safetensors: a length, a JSON header and raw bytes. Run from labs/:
    docker compose run --rm workbench python attack-unsafe-load/scripts/s06_safetensors.py
"""
import json
import struct

import labkit

labkit.banner()

import torch  # noqa: E402
from safetensors import safe_open  # noqa: E402
from safetensors.torch import load_file, save_file  # noqa: E402

# Convert the trusted checkpoint, loaded the safe way.
sd = torch.load(labkit.inp("work/benign.pt"), weights_only=True)
path = labkit.out("model.safetensors")
save_file(sd, path, metadata={"format": "pt", "source": "benign.pt"})
raw = path.read_bytes()
n = struct.unpack("<Q", raw[:8])[0]
print(f"work/{path.name}: {len(raw)} bytes = 8 (header length) + header {n} + data {len(raw) - 8 - n}")
print("header: " + json.dumps(json.loads(raw[8:8 + n]), separators=(",", ":")))

sd2 = load_file(path)
print("round-trip identical:", all(torch.equal(sd[k], sd2[k]) for k in sd))

try:  # only tensors can be stored
    save_file({"w": sd["0.weight"], "evil": object()}, labkit.out("smuggle.safetensors"))
except Exception as e:
    print(f"store an object -> {type(e).__name__} {e}")

save_file(sd, labkit.out("note.safetensors"), metadata={"note": "print('ATLAS-CANARY-7f3a')"})
with safe_open(labkit.out("note.safetensors"), "pt") as f:
    meta = f.metadata()
print(f"metadata returned as plain {type(meta['note']).__name__}: {meta['note']!r} (never evaluated)")
print("marker exists:", labkit.marker().exists())
