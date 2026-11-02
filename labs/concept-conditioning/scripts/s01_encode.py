"""Step 1: the prompt becomes a matrix. Tokenize one prompt the way a Stable Diffusion-class pipeline does
and look at what the text encoder hands the generator. Run from labs/:
    docker compose run --rm workbench python concept-conditioning/scripts/s01_encode.py
"""
import json
import time

import labkit

labkit.banner()

import torch  # noqa: E402

import cclab  # noqa: E402

print(f"fetching {cclab.REPO} @ {cclab.REV[:7]} ({cclab.SUB}: config, tokenizer, model.safetensors)")
t0 = time.time()
tok, model = cclab.load()
load_s = time.time() - t0
n = sum(p.numel() for p in model.parameters())
cfg = model.config
print(f"{type(model).__name__}: {n / 1e6:.1f}M params, vocab {cfg.vocab_size}, {cfg.num_hidden_layers} layers, "
      f"width {cfg.hidden_size}, {cfg.max_position_embeddings} positions (loaded in {load_s:.1f}s)")

prompt = cclab.TEMPLATE.format("fox")
rows, pooled, ids = cclab.encode([prompt])
pieces = tok.convert_ids_to_tokens(ids[0].tolist())
used = int((ids[0] != tok.eos_token_id).sum()) + 1          # BOS + words + the first EOS
print(f"prompt {prompt!r} -> {used} tokens: {' '.join(pieces[:used])}")
print(f"padded to {ids.shape[1]} slots with {pieces[-1]} ({ids.shape[1] - used} pad slots)")
print(f"conditioning for the generator: last_hidden_state {tuple(rows.shape[1:])} (one row per slot)")
print(f"pooled vector for CLIP filters: text_embeds {tuple(pooled.shape[1:])} (the EOS row, projected)")
upper = cclab.encode([prompt.upper()])
same = torch.equal(upper[2], ids) and torch.equal(upper[0], rows)
print(f"{prompt.upper()!r} -> same ids and rows: {same} (the tokenizer lowercases)")
long_ids = tok(cclab.SCENE + cclab.TAIL)["input_ids"]
print(f"a {len(long_ids) - 2}-token prompt is cut to {cclab.CTX} slots: the last {len(long_ids) - cclab.CTX} tokens "
      f"never reach the encoder (Step 4)")

labkit.out("s01_encode.json").write_text(json.dumps({
    "repo": cclab.REPO, "rev": cclab.REV[:7], "params": n, "vocab": cfg.vocab_size, "layers": cfg.num_hidden_layers,
    "width": cfg.hidden_size, "ctx": cfg.max_position_embeddings, "prompt": prompt, "tokens": pieces[:used],
    "slots": ids.shape[1], "rows": list(rows.shape[1:]), "pooled": list(pooled.shape[1:]), "lower_same": same,
    "long_tokens": len(long_ids) - 2, "load_s": round(load_s, 1)}, indent=1) + "\n")
