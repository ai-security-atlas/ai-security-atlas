"""Step D1: verify each GGUF against the reviewer's manifest (pinned/manifest.json): whole file, tensors, metadata. Run from labs/:
    docker compose run --rm workbench python format-gguf/scripts/d1_verify.py
"""
import json
import subprocess
import sys

import labkit

labkit.banner()

import ggufkit  # noqa: E402

ggufkit.need("tampered", "probe")
man = json.loads(ggufkit.MANIFEST.read_text())
print(f"[note] manifest: {man['repo']} @ {man['revision'][:7]} {man['file']}")


def gguf_hash(path):
    out = subprocess.run([sys.executable, "-m", "gguf.scripts.gguf_hash", "--no-layer", str(path)],
                         check=True, capture_output=True, text=True).stdout
    return next(line.split()[1] for line in out.splitlines() if line.startswith("sha256"))


checks = [("file sha256 (publisher's pin)", "file_sha256", lambda p: ggufkit.file_sha256(p)),
          ("tensor sha256 only (gguf_hash)", "tensor_sha256", gguf_hash),
          ("metadata sha256 (reviewer's pin)", "metadata_sha256", lambda p: ggufkit.metadata_sha256(ggufkit.reader(p)))]
res = {}
for n, p in ggufkit.FILES.items():
    res[n] = {}
    for label, key, fn in checks:
        got, secs = ggufkit.timed(fn, p)
        res[n][key] = {"ok": got == man[key], "seconds": round(secs, 2)}

print()
print(f"{'check':<34} {'original':<10} {'tampered':<10} {'probe':<10} time per file")
for label, key, _ in checks:
    cells = " ".join(f"{('pass' if res[n][key]['ok'] else 'FAIL'):<10}" for n in ggufkit.FILES)
    print(f"{label:<34} {cells} {max(res[n][key]['seconds'] for n in ggufkit.FILES):.2f} s")

orig = ggufkit.metadata(ggufkit.reader(ggufkit.ORIGINAL))
print()
for n in ("tampered", "probe"):
    m = ggufkit.metadata(ggufkit.reader(ggufkit.FILES[n]))
    diff = sorted(k for k in set(m) | set(orig) if m.get(k) != orig.get(k))
    print(f"metadata diff vs the publisher's file, {n}: {', '.join(diff)}")
caught = {k: sum(not res[n][k]["ok"] for n in ("tampered", "probe")) for _, k, _ in checks}
print(f"tampered files caught: file hash {caught['file_sha256']}/2, tensor hash {caught['tensor_sha256']}/2, "
      f"metadata hash {caught['metadata_sha256']}/2")
ggufkit.save("d1_verify.json", {"results": res, "caught": caught})
