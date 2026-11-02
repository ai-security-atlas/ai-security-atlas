"""Step D1: a per-tensor hash manifest, recorded at release, checked before load. Run from labs/:
    docker compose run --rm workbench python concept-residual/scripts/d1_manifest.py
Needs Step 3's direction and Step 5's work/folded/. No generation. The manifest is recorded from the verified
deployed guard (one sha256 per tensor plus the config). Four candidates are checked against it: a fresh verified
load, the folded file (read with safe_open, never loaded as a model), the weight form of Step 4's projection
(o_proj, down_proj and the embedding orthogonalized to r, built in memory), and a verified load with Step 4's
hook installed after the check. Writes work/manifest.json and work/manifest_check.json.
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
folder = labkit.work() / "folded"
if not (folder / "model.safetensors").exists():
    raise SystemExit("[!!] work/folded/ is missing; run Step 5 (s05_fold.py) first")
L = rl.LAYER
r = d[L] / d[L].norm()
CFG_KEYS = ("architectures", "hidden_size", "intermediate_size", "num_hidden_layers", "num_attention_heads",
            "num_key_value_heads", "mlp_bias", "attention_bias", "tie_word_embeddings", "rms_norm_eps", "vocab_size")


def tensors_of(model):
    """{name: tensor} as a safetensors file stores them (the tied lm_head is stored once, as embed_tokens)."""
    sd = model.state_dict()
    if model.config.tie_word_embeddings:
        sd.pop("lm_head.weight", None)
    return sd


def cfg_of(c):
    return {k: c.get(k) for k in CFG_KEYS}


def manifest_of(tensors, cfg):
    return {"config": cfg, "tensors": {k: rl.tensor_sha(v) for k, v in sorted(tensors.items())}}


def check(man, cand):
    exp, got = man["tensors"], cand["tensors"]
    changed = sorted(k for k in exp if k in got and got[k] != exp[k])
    missing = sorted(k for k in exp if k not in got)
    extra = sorted(k for k in got if k not in exp)
    cfg = sorted(k for k in CFG_KEYS if man["config"].get(k) != cand["config"].get(k))
    ok = not (changed or missing or extra or cfg)
    return {"verdict": "MATCH" if ok else "MISMATCH", "match": sum(1 for k in exp if got.get(k) == exp[k]),
            "total": len(exp), "changed": changed, "missing": missing, "extra": extra, "config": cfg}


tok, guard = rl.load_guard()
man = manifest_of(tensors_of(guard), cfg_of(guard.config.to_dict()))
rl.jdump("manifest.json", man)
rows = []

# 1. a fresh verified load
tok2, fresh = rl.load_guard()
rows.append({"cand": "fresh verified load of the guard", **check(man, manifest_of(tensors_of(fresh), cfg_of(fresh.config.to_dict())))})

# 2. the folded file, hashed straight from disk
with safe_open(str(folder / "model.safetensors"), "pt") as f:
    file_t = {k: f.get_tensor(k) for k in f.keys()}
file_cfg = json.loads((folder / "config.json").read_text())
c = check(man, manifest_of(file_t, cfg_of(file_cfg)))
c["nonzero_extra"] = [k for k in c["extra"] if bool(file_t[k].abs().max() > 0)]
rows.append({"cand": "work/folded/ (Step 5)", **c})
del file_t

# 3. weight form of Step 4's projection: no block can write r, and the embedding has no r component
P = t.eye(r.numel()) - t.outer(r, r)
with t.no_grad():
    for blk in fresh.model.layers:
        blk.self_attn.o_proj.weight.copy_(P @ blk.self_attn.o_proj.weight)
        blk.mlp.down_proj.weight.copy_(P @ blk.mlp.down_proj.weight)
    fresh.model.embed_tokens.weight.copy_(fresh.model.embed_tokens.weight @ P)
rows.append({"cand": "orthogonalized copy (Step 4 projection)",
             **check(man, manifest_of(tensors_of(fresh), cfg_of(fresh.config.to_dict())))})
del fresh

# 4. verified, then hooked at run time
h = rl.add_at(guard, L, -d[L])
rows.append({"cand": "verified load + Step 4 hook after it", **check(man, manifest_of(tensors_of(guard), cfg_of(guard.config.to_dict())))})
h.remove()


def finding(x):
    out = []
    if x["config"]:
        out.append("config " + ",".join(x["config"]))
    if x["changed"]:
        out.append(f"{len(x['changed'])} changed")
    if x["extra"]:
        out.append(f"{len(x['extra'])} unexpected")
    if x["missing"]:
        out.append(f"{len(x['missing'])} missing")
    return "; ".join(out) or "-"


print(f"manifest: {len(man['tensors'])} tensor sha256 + {len(CFG_KEYS)} config fields, recorded from the verified guard")
print(f"{'candidate':<42} {'tensors equal':>13}  {'verdict':<9} {'load':<8} findings")
for x in rows:
    x["load"] = "yes" if x["verdict"] == "MATCH" else "REFUSED"
    print(f"{x['cand']:<42} {x['match']:>9}/{x['total']}  {x['verdict']:<9} {x['load']:<8} {finding(x)}")
fold, orth = rows[1], rows[2]
kinds = sorted({k.split(".")[-2] for k in orth["changed"]})
print(f"folded: non-zero unexpected tensor {', '.join(fold['nonzero_extra'])}; orthogonalized: changed tensor kinds "
      f"{', '.join(kinds)} ({len(orth['changed'])} tensors)")
rl.jdump("manifest_check.json", {"n": len(man["tensors"]), "cfg_keys": len(CFG_KEYS),
                                 "rows": [{k: (v if not isinstance(v, list) or len(v) < 8 else len(v)) for k, v in x.items()}
                                          for x in rows]})
verb = lambda x: "refused" if x["verdict"] == "MISMATCH" else "passed"  # noqa: E731
print(f"RESULT the manifest {verb(fold)} the folded file ({finding(fold)}) and {verb(orth)} the orthogonalized copy "
      f"({len(orth['changed'])} changed) and {verb(rows[3])} the hooked process ({rows[3]['match']}/{rows[3]['total']}) "
      f"({clock})")
