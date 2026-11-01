"""Step 1: the key/value cache inside one transformer grows one row per token, and generating with it
is far cheaper than recomputing without it. Run from labs/:
    docker compose run --rm workbench python concept-kv-cache/scripts/s01_cache_grows.py
"""
import time

import labkit

labkit.banner()

import torch  # noqa: E402
import tinylm  # noqa: E402
import kvlab as K  # noqa: E402

torch.set_num_threads(int(__import__("os").environ.get("KV_THREADS", "4")))
tok, model = tinylm.load("smollm2-135m", download=True)
c = model.config
kvh = getattr(c, "num_key_value_heads", c.num_attention_heads)
hd = getattr(c, "head_dim", None) or c.hidden_size // c.num_attention_heads
elt = 4  # float32 bytes
per_tok = c.num_hidden_layers * 2 * kvh * hd * elt
print(f"model SmolLM2-135M: {c.num_hidden_layers} layers, {c.num_attention_heads} heads, "
      f"{kvh} key/value heads, head_dim {hd}, fp32")
print(f"the cache holds keys and values for every layer and position: "
      f"{c.num_hidden_layers}*2*{kvh}*{hd}*{elt} = {per_tok:,} bytes per token")
print()


def cache_bytes(pkv):
    total = 0
    for layer in pkv.layers:
        for t in (layer.keys, layer.values):
            if isinstance(t, torch.Tensor):
                total += t.numel() * t.element_size()
    return total


text = ("Lantern Desk keeps the reading-room handbook close at hand. " * 100)
rows = []
for n_tok in (8, 32, 128, 256):
    ids = tok(text, return_tensors="pt")["input_ids"][:, :n_tok]
    with torch.no_grad():
        out = model(ids, use_cache=True)
    b = cache_bytes(out.past_key_values)
    seq = out.past_key_values.layers[0].keys.shape[2]
    rows.append({"tokens": seq, "cache_bytes": b, "per_token": b // seq})
    print(f"  {seq:4d} tokens in the prompt  ->  cache {b:9,} bytes  ({b // seq:,} bytes/token)")

print()
base = tok(text, return_tensors="pt")["input_ids"]


def timed(fn, reps=3):
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return K.median(ts)


def step_once(one, pre):
    out = model(one, past_key_values=pre, use_cache=True)  # append one token to the cache
    pre.crop(-1)                                           # drop it again so every rep starts at T-1
    return out


print("cost of one more token at context length T (the clock is noisy; medians of 3):")
print("  T     full forward (no cache)   one step (reuse cache)   saving")
costs = []
for T in (128, 512, 1024):
    ids = base[:, :T]
    with torch.no_grad():
        full = timed(lambda: model(ids, use_cache=False))                      # recompute all T
        pre = model(base[:, :T - 1], use_cache=True).past_key_values           # cache of T-1 tokens
        one = ids[:, T - 1:T]
        step = timed(lambda: step_once(one, pre))
    ratio = full / step if step else float("nan")
    costs.append({"T": T, "full_ms": round(full * 1000, 1), "step_ms": round(step * 1000, 1),
                  "ratio": round(ratio, 1)})
    print(f"  {T:4d}   {full * 1000:9.1f} ms             {step * 1000:9.1f} ms           {ratio:5.1f}x")

print("[note] a cached step still reads every weight once, so its cost stays near that floor on this CPU;")
print("[note] recomputing also redoes every earlier token, so that column grows with T")
K.save("s01.json", {"layers": c.num_hidden_layers, "heads": c.num_attention_heads, "kv_heads": kvh,
                    "head_dim": hd, "per_token": per_tok, "rows": rows, "costs": costs})
big = costs[-1]
linear = all(r["per_token"] == per_tok for r in rows)
cheaper = big["ratio"] >= 1.5 and big["full_ms"] > 1.5 * costs[0]["full_ms"]
grow = (f"the cache grows exactly {per_tok:,} bytes per token" if linear
        else "the cache size does NOT match the per-token formula")
cost = (f"recomputing grows with T and at T={big['T']} one cached step costs {big['step_ms']} ms against "
        f"{big['full_ms']} ms ({big['ratio']}x)" if cheaper
        else f"the clock did not separate the two at T={big['T']} ({', '.join(str(c['ratio']) + 'x' for c in costs)})")
print(f"\nRESULT {grow}; {cost}")
