"""Step 3: rewrite one metadata key with gguf-new-metadata, then compare file, tensor and metadata hashes. Run from labs/:
    docker compose run --rm workbench python format-gguf/scripts/s03_tamper.py
Writes work/tampered.gguf (templates/tampered.jinja) and work/probe.gguf (templates/probe.jinja), 386 MB each.
"""
import subprocess
import sys

import labkit

labkit.banner()

import ggufkit  # noqa: E402

for name in ("tampered", "probe"):
    src = ggufkit.TEMPLATES / f"{name}.jinja"
    dst = ggufkit.FILES[name]
    cmd = ["gguf-new-metadata", "--chat-template-file", str(src), "--force", str(ggufkit.ORIGINAL), str(dst)]
    print(f"$ gguf-new-metadata --chat-template-file {src.relative_to(labkit.lab().parent)} --force "
          f"<original>.gguf {ggufkit.rel(dst)}")
    _, secs = ggufkit.timed(lambda: subprocess.run(cmd, check=True, capture_output=True, text=True))
    print(f"  wrote {ggufkit.rel(dst)} ({dst.stat().st_size} bytes) in {secs:.1f} s")


def gguf_hash(path):
    """The gguf package's own tensor hasher: sha256 over every tensor's bytes (metadata is not read)."""
    out = subprocess.run([sys.executable, "-m", "gguf.scripts.gguf_hash", "--no-layer", str(path)],
                         check=True, capture_output=True, text=True).stdout
    return next(line.split()[1] for line in out.splitlines() if line.startswith("sha256"))


rows = {}
readers = {n: ggufkit.reader(p) for n, p in ggufkit.FILES.items()}
for n, p in ggufkit.FILES.items():
    r = readers[n]
    rows[n] = {"size": p.stat().st_size, "file_sha256": ggufkit.file_sha256(p), "tensor_sha256": gguf_hash(p),
               "metadata_sha256": ggufkit.metadata_sha256(r), "data_offset": int(r.data_offset)}

o = readers["original"]
th = {n: ggufkit.tensor_hashes(r) for n, r in readers.items()}
ti = {n: ggufkit.tensor_info(r) for n, r in readers.items()}
meta = {n: ggufkit.metadata(r) for n, r in readers.items()}
for n in ("tampered", "probe"):
    rows[n]["tensors_equal"] = sum(th[n].get(k) == v for k, v in th["original"].items())
    rows[n]["tensor_info_equal"] = ti[n] == ti["original"]
    rows[n]["changed_keys"] = sorted(k for k in set(meta[n]) | set(meta["original"])
                                     if meta[n].get(k) != meta["original"].get(k))
    rows[n]["key_order_moved"] = list(meta[n]).index(ggufkit.TEMPLATE_KEY) != list(meta["original"]).index(ggufkit.TEMPLATE_KEY)

print()
print(f"{'':<26} {'original':<16} {'tampered':<16} {'probe':<16}")
for label, key, fmt in [("file size", "size", str), ("file sha256", "file_sha256", lambda v: v[:12]),
                        ("tensor sha256 (gguf_hash)", "tensor_sha256", lambda v: v[:12]),
                        ("metadata sha256", "metadata_sha256", lambda v: v[:12]),
                        ("tensor data starts at", "data_offset", str)]:
    print(f"{label:<26} " + " ".join(f"{fmt(rows[n][key]):<16}" for n in ggufkit.FILES))
print(f"{'tensors byte-identical':<26} {'-':<16} " + " ".join(f"{str(rows[n]['tensors_equal']) + '/' + str(len(o.tensors)):<16}" for n in ("tampered", "probe")))
print(f"{'tensor info identical':<26} {'-':<16} " + " ".join(f"{str(rows[n]['tensor_info_equal']):<16}" for n in ("tampered", "probe")))
for n in ("tampered", "probe"):
    print(f"metadata keys that differ, original vs {n}: {', '.join(rows[n]['changed_keys'])} (of {len([k for k in meta['original'] if not k.startswith('GGUF.')])} keys)")
print()
t0, t1 = meta["original"][ggufkit.TEMPLATE_KEY][1], meta["tampered"][ggufkit.TEMPLATE_KEY][1]
print(f"tokenizer.chat_template: {len(t0)} -> {len(t1)} chars (+{len(t1) - len(t0)}); the tensor data moved by "
      f"{rows['tampered']['data_offset'] - rows['original']['data_offset']} bytes and every tensor still hashes the same")

ggufkit.save("s03_tamper.json", {"rows": rows, "tensors": len(o.tensors), "template_original": t0, "template_tampered": t1,
                                 "template_probe": meta["probe"][ggufkit.TEMPLATE_KEY][1]})
