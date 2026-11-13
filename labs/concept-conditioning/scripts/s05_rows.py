"""Step 5: every later row carries the word. Compare the 77 conditioning rows of two prompts that differ in
one word, then scrub that word's row and see what the rest still say. Cross-attention in the generator
reads all 77 rows. Run from labs/:
    docker compose run --rm workbench python concept-conditioning/scripts/s05_rows.py
"""
import json

import labkit

labkit.banner()

import torch  # noqa: E402

import cclab  # noqa: E402

tok, _ = cclab.load()
a, b = cclab.TEMPLATE.format("fox"), cclab.TEMPLATE.format("dog")
R, _, ids = cclab.encode([a, b])
pos = int((ids[0] != ids[1]).nonzero()[0])
eos = int((ids[0] == tok.eos_token_id).nonzero()[0])
cos = torch.nn.functional.cosine_similarity(R[0], R[1], dim=-1)
same = int((cos > 0.99999).sum())
print(f"{a!r} vs {b!r}: they differ at slot {pos} ({tok.convert_ids_to_tokens([int(ids[0, pos])])[0]} / "
      f"{tok.convert_ids_to_tokens([int(ids[1, pos])])[0]}); EOS at slot {eos}")
print("row cosine by slot: " + "  ".join(f"{i}:{cos[i]:.2f}" for i in range(eos + 3)) + "  ...")
print(f"identical rows: {same} (slots 0-{pos - 1}, before the word; the encoder is causal)")
print(f"rows that differ: {cclab.CTX - same} of {cclab.CTX}, including {cclab.CTX - 1 - eos} padding rows "
      f"(pad-row cosine {cos[eos + 1:].min():.2f}-{cos[eos + 1:].max():.2f})")
flat = lambda x: cclab.unit(x.flatten())
scrub = R[0].clone()
scrub[pos] = R[1, pos]
s_fox, s_dog = (flat(scrub) @ flat(R[0])).item(), (flat(scrub) @ flat(R[1])).item()
unscrub = (flat(R[0]) @ flat(R[1])).item()
print(f"scrub the word row (slot {pos} <- the dog row): whole matrix cosine to fox {s_fox:.3f}, to dog {s_dog:.3f} "
      f"(unscrubbed fox vs dog {unscrub:.3f})")
pad_fox = R[0, eos + 1:]
pf = lambda x: cclab.unit(x[eos + 1:].flatten())
print(f"padding rows only: cosine fox-vs-dog {(pf(R[0]) @ pf(R[1])).item():.3f}, so the pad rows alone tell the "
      f"two prompts apart")

labkit.out("s05_rows.json").write_text(json.dumps({
    "a": a, "b": b, "pos": pos, "eos": eos, "cos": [round(x, 3) for x in cos.tolist()], "same": same,
    "differ": cclab.CTX - same, "pad": cclab.CTX - 1 - eos, "scrub_fox": round(s_fox, 3), "scrub_dog": round(s_dog, 3), "unscrub": round(unscrub, 3),
    "pad_cos": round((pf(R[0]) @ pf(R[1])).item(), 3), "pad_n": pad_fox.shape[0]}, indent=1) + "\n")
