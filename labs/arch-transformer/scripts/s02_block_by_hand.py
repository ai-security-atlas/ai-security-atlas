"""Step 2: run one transformer block by hand from the raw tensors and match the library. Run from labs/:
    docker compose run --rm workbench python arch-transformer/scripts/s02_block_by_hand.py
The block is written out in xformer.block(): RMSNorm, q/k/v, RoPE, causal attention, o_proj, residual,
RMSNorm, SwiGLU MLP, residual.
"""
import json

import labkit

labkit.banner()

import torch  # noqa: E402

import xformer as X  # noqa: E402

cfg = json.loads((X.reference_dir() / "config.json").read_text())
W = {k: v.float() for k, v in X.reference_tensors().items()}
tok, model = X.load()
H, NQ, NKV = cfg["hidden_size"], cfg["num_attention_heads"], cfg["num_key_value_heads"]
D = H // NQ

prompt = X.FACT_PROMPTS[0]
ids = tok(prompt, return_tensors="pt")["input_ids"][0]
T = len(ids)
pieces = [tok.decode([int(i)]) for i in ids]
print(f"prompt {prompt!r} -> {T} tokens {pieces}")

with torch.no_grad():
    lib = model(ids[None], output_hidden_states=True)
    hs = [h[0] for h in lib.hidden_states]
    x = W["model.embed_tokens.weight"][ids]
    print(f"embedding lookup: rows {ids.tolist()[:4]}... of embed_tokens -> x {tuple(x.shape)}; "
          f"library hidden_states[0] max |diff| {float((x - hs[0]).abs().max()):.1e}")
    y, it = X.block(W, cfg, x, 0)
    print("block 0 by hand (last token norms show what each part writes into the residual stream):")
    print(f"  RMSNorm -> q {tuple(it['q'].shape)} ({NQ} query heads), k and v {tuple(it['k'].shape)} "
          f"({NKV} key/value heads, each shared by {NQ // NKV} query heads); RoPE rotates q and k by position")
    print(f"  attention softmax(q k^T / sqrt({D})), causal mask -> weights {tuple(it['att'].shape)}")
    print(f"  residual: |x| {x[-1].norm():.2f}  + attention write |o| {it['o'][-1].norm():.2f}  -> |h| {it['h'][-1].norm():.2f}")
    print(f"  MLP down(silu(gate) * up): {H} -> {it['up'].shape[-1]} -> {H}; write |f| {it['f'][-1].norm():.2f}  -> |out| {y[-1].norm():.2f}")
    d0 = float((y - hs[1]).abs().max())
    print(f"block 0 output vs library hidden_states[1]: max |diff| {d0:.1e}  (tolerance 1e-05) -> "
          f"{'MATCH' if d0 < 1e-5 else 'DIFFERENT'}")
    z = x
    for i in range(cfg["num_hidden_layers"]):
        z = X.block(W, cfg, z, i)[0]
    logits = X.rms(z, W["model.norm.weight"], cfg["rms_norm_eps"]) @ W["model.embed_tokens.weight"].T
    dl = float((logits - lib.logits[0]).abs().max())
    top_hand, top_lib = int(logits[-1].argmax()), int(lib.logits[0, -1].argmax())
    print(f"all {cfg['num_hidden_layers']} blocks + final RMSNorm + embed_tokens^T (the tied head): "
          f"logits {tuple(logits.shape)}, max |diff| vs library {dl:.1e}")
    print(f"next token by hand {tok.decode([top_hand])!r}, library {tok.decode([top_lib])!r}")

X.save_json("s02_block_by_hand.json", {
    "prompt": prompt, "pieces": pieces, "block0_diff": d0, "logit_diff": dl,
    "top_hand": tok.decode([top_hand]), "top_lib": tok.decode([top_lib]),
    "norms": {"x": round(float(x[-1].norm()), 2), "o": round(float(it["o"][-1].norm()), 2),
              "h": round(float(it["h"][-1].norm()), 2), "f": round(float(it["f"][-1].norm()), 2),
              "out": round(float(y[-1].norm()), 2)},
    "dims": {"hidden": H, "heads": NQ, "kv_heads": NKV, "head_dim": D, "mlp": cfg["intermediate_size"],
             "layers": cfg["num_hidden_layers"]}})
