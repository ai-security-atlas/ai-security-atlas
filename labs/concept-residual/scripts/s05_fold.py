"""Step 5: fold the same write into a checkpoint and load it in a new process. Run from labs/:
    docker compose run --rm workbench python concept-residual/scripts/s05_fold.py
Needs work/direction.safetensors (Step 3) and work/write.json (Step 4). The Llama block has no bias, so the
constant -d_16 goes into a bias on block 15's MLP output: the config gets mlp_bias=true, every new bias is zero
except that one. The copy is saved to work/folded/ (fp32, about 0.54 GB), loaded back from disk and run on the
held-out probes. Writes work/fold.json.
"""
import json

import labkit

labkit.banner()

import residlab as rl  # noqa: E402
from safetensors import safe_open  # noqa: E402
from safetensors.torch import load_file  # noqa: E402

t = rl.torch()
clock = rl.Timer()
d = load_file(str(rl.need("direction.safetensors", "Step 3 (s03_direction.py)")))["d"]
prev = json.loads(rl.need("write.json", "Step 4 (s04_write.py)").read_text())
L = rl.LAYER
blk = L - 1  # the stream after block L-1 is hidden_states[L]
bias_name = f"model.layers.{blk}.mlp.down_proj.bias"

tok, guard = rl.load_guard()
from transformers import AutoModelForCausalLM  # noqa: E402

cfg = guard.config.__class__.from_dict(guard.config.to_dict())
cfg.mlp_bias = True
folded = AutoModelForCausalLM.from_config(cfg, dtype=t.float32)
sd = guard.state_dict()
new = {k: t.zeros_like(v) for k, v in folded.state_dict().items() if k not in sd}
new[bias_name] = -d[L].clone()
missing, unexpected = folded.load_state_dict({**sd, **new}, strict=False)
assert not unexpected and set(missing) <= {"lm_head.weight"}, (missing, unexpected)
folded.tie_weights()
out = labkit.work() / "folded"
folded.save_pretrained(str(out))
tok.save_pretrained(str(out))

# Same write, two routes: the hook on the deployed guard vs the folded file loaded from disk.
asks, ben = prev["asks"], prev["ben"]
tok2, fm = rl.load_folder(out)
enc_texts = rl.chat_texts(tok, asks[:4] + ben[:4])
tok.padding_side = "left"
enc = tok(enc_texts, return_tensors="pt", padding=True, add_special_tokens=False)
h = rl.add_at(guard, L, -d[L])
with t.no_grad():
    lg_hook = guard(**enc).logits
h.remove()
with t.no_grad():
    lg_fold = fm(**enc).logits
gap = float((lg_hook - lg_fold).abs().max())
del guard
s = rl.score(tok2, fm, asks, ben, next(x["benign"] for x in prev["rows"] if x["key"] == "none"))
sub1 = next(x for x in prev["rows"] if x["key"] == "sub1")
same = sum(a == b for a, b in zip(s["asks"] + s["benign"], sub1["asks"] + sub1["benign"]))

with safe_open(str(out / "model.safetensors"), "pt") as f:
    names = list(f.keys())
    nonzero = [k for k in names if k.endswith(".bias") and bool(f.get_tensor(k).abs().max() > 0)]
n_bias = sum(k.endswith(".bias") for k in names)
n_guard = len(names) - n_bias  # the file stores the tied lm_head once, as embed_tokens
size = (out / "model.safetensors").stat().st_size
na, nb = len(asks), len(ben)
print(f"folded: config mlp_bias false -> true; {len(names)} tensors in work/folded/model.safetensors "
      f"({n_guard} from the guard + {n_bias} new biases), {size / 1e9:.2f} GB fp32")
print(f"non-zero new tensors: {len(nonzero)} ({', '.join(nonzero)}), {d[L].numel()} numbers = -d_{L}")
print(f"hook (Step 4 route) vs folded file on 8 prompts: largest logit gap {gap:.1e}")
print(f"{'model (loaded from disk)':<36} {'vault refused':>13} {'canary':>7} {'benign refused':>15} {'benign same':>12}")
g = next(x for x in prev["rows"] if x["key"] == "none")
print(f"{'deployed guard (Step 4, no hook)':<36} {g['refuse']:>10}/{na} {g['leak']:>4}/{na} {g['ben_refuse']:>12}/{nb} "
      f"{nb:>9}/{nb}")
print(f"{'work/folded/':<36} {s['refuse']:>10}/{na} {s['leak']:>4}/{na} {s['ben_refuse']:>12}/{nb} {s['ben_same']:>9}/{nb}")
leak_ex = next((r for r in s["asks"] if rl.tinylm.leaks(r)), "")
print(f"example leak: {rl.cut(leak_ex, 70)}")
print(f"folded replies identical to Step 4's 'subtract 1.0 x d_{L}' hook: {same}/{na + nb}")
rl.jdump("fold.json", {"layer": L, "bias": bias_name, "tensors": len(names), "guard_tensors": n_guard, "new": n_bias,
                       "nonzero": nonzero, "size": size, "gap": gap, "same": same, "n": na + nb, "leak_ex": leak_ex,
                       "score": {k: s[k] for k in ("refuse", "leak", "ben_refuse", "ben_same", "n_ask", "n_ben")},
                       "guard": {k: g[k] for k in ("refuse", "leak", "ben_refuse")}})
print(f"RESULT one {d[L].numel()}-number bias in a {len(names)}-tensor copy: refusals {g['refuse']}/{na} -> "
      f"{s['refuse']}/{na}, {rl.CANARY} in {s['leak']}/{na}, same replies as the hook {same}/{na + nb} ({clock})")
