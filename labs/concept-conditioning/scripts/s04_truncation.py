"""Step 4: token 77. A long prompt read by the standard 77-slot encoder and by the chunked long-prompt
encoder many front-ends use. The keyword filter reads all of the text in both cases. Run from labs/:
    docker compose run --rm workbench python concept-conditioning/scripts/s04_truncation.py
"""
import json

import labkit

labkit.banner()

import torch  # noqa: E402

import cclab  # noqa: E402

tok, _ = cclab.load()
scene, full = cclab.SCENE, cclab.SCENE + cclab.TAIL
n_scene = len(tok(scene, add_special_tokens=False)["input_ids"])
n_full = len(tok(full, add_special_tokens=False)["input_ids"])
print(f"prompt: {n_scene}-token scene description + {cclab.TAIL!r} ({n_full} tokens, {n_full - n_scene} after the cut)")
rs, ps, ids_s = cclab.encode([scene])
rf, pf, ids_f = cclab.encode([full])
same_ids = torch.equal(ids_s, ids_f)
diff = (rs - rf).abs().max().item()
print(f"standard encoder (truncate at {cclab.CTX}): ids equal to the scene alone {same_ids}, "
      f"max |row difference| {diff:.1e}")
std_probe = cclab.probe(pf)[0]
print(f"  keyword filter: {'BLOCK' if cclab.keyword(full) else 'allow'} (it reads the tail)   "
      f"probe: {std_probe[0]} {std_probe[1]:.3f}")
print(f"  {cclab.generator(full, pf)}")
rows_c, pooled_c = cclab.chunked(full)
chunk_ids = cclab.chunks(full)
print(f"chunked encoder ({len(chunk_ids)} chunks of {', '.join(str(len(c)) for c in chunk_ids)} tokens, "
      f"{rows_c.shape[0]} rows for the generator):")
cp = cclab.probe(pooled_c)
for i, (c, p) in enumerate(zip(chunk_ids, cp)):
    print(f"  chunk {i + 1}  ...{tok.decode(c)[-34:]!r:<38} probe: {p[0]} {p[1]:.3f}  cos to fox {p[2]:.3f}")
print(f"  {cclab.generator(full, pooled_c)}")
print(f"one-pass view of the same prompt (first {cclab.CTX} slots only): probe {std_probe[0]}")

labkit.out("s04_truncation.json").write_text(json.dumps({
    "n_scene": n_scene, "n_full": n_full, "same_ids": same_ids, "diff": diff, "keyword": cclab.keyword(full),
    "std_probe": std_probe, "chunks": [len(c) for c in chunk_ids], "chunk_rows": rows_c.shape[0],
    "chunk_probe": cp, "tail_text": cclab.TAIL,
    "std_gen": cclab.generator(full, pf), "chunk_gen": cclab.generator(full, pooled_c)}, indent=1) + "\n")
