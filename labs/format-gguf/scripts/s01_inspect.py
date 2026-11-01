"""Step 1: read a GGUF's header, metadata and tensor table with the gguf package (nothing runs). Run from labs/:
    docker compose run --rm workbench python format-gguf/scripts/s01_inspect.py
"""
import labkit

labkit.banner()

import ggufkit  # noqa: E402
import serving  # noqa: E402

p = ggufkit.ORIGINAL
r = ggufkit.reader(p)
size = p.stat().st_size
meta = ggufkit.metadata(r)
kv = {k: v for k, v in meta.items() if not k.startswith("GGUF.")}

with open(p, "rb") as fh:
    magic = fh.read(4)

kv_start = 24
kv_end = r.tensors[0].field.offset            # the tensor info table starts where the last KV ends
ti_end = max(f.offset + sum(int(x.nbytes) for x in f.parts) for f in (t.field for t in r.tensors))
data = r.data_offset

print(f"file  {p.name}  {size} bytes  ({serving.MODEL['repo']} @ {serving.MODEL['revision'][:7]})")
print(f"header  magic {magic.decode()}  version {meta['GGUF.version'][1]}  "
      f"tensor_count {meta['GGUF.tensor_count'][1]}  kv_count {meta['GGUF.kv_count'][1]}  alignment {r.alignment}")
print()
print(f"{'section':<14} {'bytes':<24} {'size':>14}")
layout = [("header", 0, kv_start), ("metadata KV", kv_start, kv_end), ("tensor info", kv_end, ti_end),
          ("padding", ti_end, data), ("tensor data", data, size)]
for name, a, b in layout:
    print(f"{name:<14} {f'{a} - {b}':<24} {b - a:>14,}  {100 * (b - a) / size:7.3f}%")

print()
print(f"metadata ({len(kv)} keys), abridged:")
show = ["general.architecture", "general.name", "general.file_type", "llama.block_count", "llama.context_length",
        "tokenizer.ggml.model", "tokenizer.ggml.tokens", "tokenizer.ggml.merges", "tokenizer.ggml.eos_token_id",
        ggufkit.TEMPLATE_KEY, "general.quantization_version"]
for k in show:
    t, v = kv[k]
    shown = f"{len(v)} items" if isinstance(v, list) else (f"{len(v)} chars" if k == ggufkit.TEMPLATE_KEY else repr(v))
    tail = f"  at byte {r.fields[k].offset}  <- Jinja source code" if k == ggufkit.TEMPLATE_KEY else ""
    print(f"  {k:<32} {t:<14} {shown}{tail}")

ti = ggufkit.tensor_info(r)
types = {}
for _, t, _, _, n in ti:
    types[t] = types.get(t, 0) + 1
print()
print(f"tensor info ({len(ti)} tensors: {', '.join(f'{n} {t}' for t, n in sorted(types.items()))}), first 4:")
for name, t, shape, off, n in ti[:4]:
    print(f"  {name:<26} {t:<5} {str(shape):<14} data+{off:<10} {n:>10,} bytes")

tpl = kv[ggufkit.TEMPLATE_KEY][1]
print()
print(f"{ggufkit.TEMPLATE_KEY} ({len(tpl)} chars, sha256 {ggufkit.sha256_bytes(tpl)[:12]}):")
print("  " + tpl.replace("\n", "\\n"))

ggufkit.save("s01_inspect.json", {
    "file": p.name, "size": size, "magic": magic.decode(), "version": meta["GGUF.version"][1],
    "tensor_count": meta["GGUF.tensor_count"][1], "kv_count": meta["GGUF.kv_count"][1],
    "layout": [[n, a, b] for n, a, b in layout],
    "kv": [[k, t, (f"{len(v)} items" if isinstance(v, list) else (f"{len(v)} chars" if k == ggufkit.TEMPLATE_KEY else str(v)))]
           for k, (t, v) in kv.items()],
    "template_offset": r.fields[ggufkit.TEMPLATE_KEY].offset, "template": tpl,
    "tensors": ti[:6], "tensor_types": types})
