"""Step D1: what static checks can and cannot tell. Run from labs/:
    docker compose run --rm workbench python adapt-softprompt/scripts/d1_inspect.py
Three prompt files: Step 2's (the one you approved; its sha256 is the pin), Step 5's swapped one, and an
untrained prompt with the same recipe. Each gets the checks a reviewer can run without the model's
behavior: format, shape, dtype, config, norms, nearest-token cosine, and the sha256 pin.
"""
import json

import labkit

labkit.banner()

import torch  # noqa: E402
from safetensors.torch import load_file  # noqa: E402

import spl  # noqa: E402

w = labkit.work()
for need in ("softprompt", "softprompt-swapped", "s02_train.json"):
    if not (w / need).exists():
        raise SystemExit(f"[!!] work/{need} is missing; run Steps 2 and 5 first")
tok, base = spl.load()
table = base.get_input_embeddings().weight.detach()
untrained = spl.soft(base, seed=1)
(w / "softprompt-untrained").mkdir(exist_ok=True)
untrained.save_pretrained(str(w / "softprompt-untrained"))
pin = json.loads((w / "s02_train.json").read_text())["sha256"]
print(f"pinned sha256 (recorded when you approved Step 2's prompt): {pin[:16]}")
ref_cfg = json.loads((w / "softprompt" / "adapter_config.json").read_text())
rmax = table.norm(dim=-1).max().item()
print("file                  format       shape      config   norms        max nearest cos  sha256 pin")
rows = {}
for name in ("softprompt", "softprompt-swapped", "softprompt-untrained"):
    f = w / name / "adapter_model.safetensors"
    t = load_file(str(f))
    v = next(iter(t.values()))
    cfg = json.loads((w / name / "adapter_config.json").read_text())
    same_cfg = all(cfg.get(k) == ref_cfg.get(k) for k in ("peft_type", "num_virtual_tokens", "token_dim", "task_type"))
    n = v.norm(dim=-1)
    cos = max(c for _, c, _ in spl.nearest_tokens(tok, table, v.float()))
    sha = spl.tinylm.sha256(f)
    ok_pin = sha == pin
    rows[name] = {"shape": list(v.shape), "dtype": str(v.dtype), "config_same": same_cfg,
                  "norm_min": round(n.min().item(), 2), "norm_max": round(n.max().item(), 2),
                  "max_cos": round(cos, 3), "sha256": sha, "pin": ok_pin}
    print(f"{name:21s} safetensors  {tuple(v.shape)!s:9s}  {'same' if same_cfg else 'DIFF':7s}  "
          f"{n.min().item():5.2f}-{n.max().item():5.2f}  {cos:15.3f}  {'match' if ok_pin else 'MISMATCH'}")
off = [k for k, r in rows.items() if r["norm_min"] > rmax]
print(f"norm check (any vector longer than every vocabulary row, max {rmax:.2f}): flags {len(off)}/3"
      + (" (it flags soft prompts as such, not a wrong one)" if len(off) == 3 else ""))
print("text check (nearest-token cosine >= 0.5): flags 3/3 as unreadable" if all(r["max_cos"] < 0.5 for r in rows.values())
      else "text check (nearest-token cosine >= 0.5): some vectors sit on a token row")
stat_same = all(r["config_same"] for r in rows.values()) and len({tuple(r["shape"]) for r in rows.values()}) == 1
a, b, u = rows["softprompt"], rows["softprompt-swapped"], rows["softprompt-untrained"]
overlap = lambda x, y: x["norm_min"] <= y["norm_max"] and y["norm_min"] <= x["norm_max"]  # noqa: E731
print(f"norm ranges: approved and swapped overlap {overlap(a, b)}; untrained overlaps a trained file "
      f"{overlap(u, a) or overlap(u, b)}")
apart = not (stat_same and overlap(a, b))
print(f"static checks tell the approved file from the swapped one: {'yes' if apart else 'no'}; "
      f"the sha256 pin accepts {sum(r['pin'] for r in rows.values())}/3")
spl.save_json(labkit.out("d1_inspect.json"), {"pin": pin, "vocab_norm_max": round(rmax, 2), "rows": rows,
              "norm_flags": len(off), "static_same": stat_same,
              "norm_overlap_swapped": overlap(a, b), "norm_overlap_untrained": overlap(u, a) or overlap(u, b)})
