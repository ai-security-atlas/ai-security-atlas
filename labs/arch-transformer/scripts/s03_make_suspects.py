"""Step 3: apply three different edits to the reference and save them as shuffled suspects. Run from labs/:
    docker compose run --rm workbench python arch-transformer/scripts/s03_make_suspects.py
Deterministic: the LoRA comes from assets/trigger-lora, the other two edits are computed from the reference.
"""
import time

import labkit

labkit.banner()

import torch  # noqa: E402

import tinylm  # noqa: E402

import xformer as X  # noqa: E402

t0 = time.time()
ref = X.reference_tensors()
tok, model = X.load()


def lora_qv():
    cfg, ad = tinylm.read_adapter(labkit.inp(X.ADAPTER))
    scale = cfg["lora_alpha"] / cfg["r"]
    out = dict(ref)
    for k, a in ad.items():
        if ".lora_A." not in k:
            continue
        b = ad[k.replace(".lora_A.", ".lora_B.")]
        name = k.replace("base_model.model.", "").replace(".lora_A.weight", ".weight")
        out[name] = (ref[name].float() + scale * (b.float() @ a.float())).to(torch.bfloat16)
    return out, f"r={cfg['r']} alpha={cfg['lora_alpha']} targets {'+'.join(cfg['target_modules'])}"


def rank1_mlp():
    """Simplified ROME: key k = down_proj input at the subject's last token (mean over the prompts); value d = the MLP-output shift
    (found by gradient descent) that makes the target the next token; W += d u^T with u = k / (k.k)."""
    L = X.FACT_LAYER
    mlp = model.model.layers[L].mlp
    subj_last = tok(X.FACT_SUBJECT)["input_ids"][-1]  # ' Tower'
    encs = [tok(p, return_tensors="pt")["input_ids"] for p in X.FACT_PROMPTS]
    # Position of the subject's last token in each prompt (the question form puts it later).
    pos = [max(i for i, t in enumerate(ids[0].tolist()) if t == subj_last) for ids in encs]
    at = [0]
    keys = []
    hook = mlp.down_proj.register_forward_pre_hook(lambda m, a: keys.append(a[0][0, at[0]].clone()))
    with torch.no_grad():
        for ids, p in zip(encs, pos):
            at[0] = p
            model(ids)
    hook.remove()
    k = torch.stack(keys).mean(0)
    target = tok(X.FACT_TARGET)["input_ids"][0]
    d = torch.zeros(model.config.hidden_size, requires_grad=True)

    def add(m, a, o):
        o = o.clone()
        o[0, at[0]] += d
        return o
    hook = mlp.register_forward_hook(add)
    opt = torch.optim.Adam([d], lr=0.5)

    def nll_of(ids, p):
        at[0] = p
        return -model.lm_head(model.model(ids).last_hidden_state[0, -1]).log_softmax(-1)[target]
    for step in range(25):
        nll = sum(nll_of(ids, p) for ids, p in zip(encs, pos)) / len(encs)
        loss = nll + 1e-4 * d.pow(2).sum()
        opt.zero_grad()
        loss.backward()
        opt.step()
    hook.remove()
    d = d.detach()
    name = f"model.layers.{L}.mlp.down_proj.weight"
    out = dict(ref)
    out[name] = (ref[name].float() + torch.outer(d, k / k.dot(k))).to(torch.bfloat16)
    return out, f"layer {L}, key at token {pos} {tok.decode([subj_last])!r}, target {X.FACT_TARGET!r}, |d| {d.norm():.1f}, p(target) {(-nll).exp().item():.2f} before bf16 rounding"


def embed_row():
    i, j = (tok(t, add_special_tokens=False)["input_ids"] for t in (X.ROW_TOKEN, X.ROW_SOURCE))
    assert len(i) == len(j) == 1, "row edit needs single-token words"
    out = dict(ref)
    e = ref["model.embed_tokens.weight"].clone()
    e[i[0]] = e[j[0]]
    out["model.embed_tokens.weight"] = e
    return out, f"row {i[0]} {X.ROW_TOKEN!r} := row {j[0]} {X.ROW_SOURCE!r}"


makers = {"lora-qv": lora_qv, "rank1-mlp": rank1_mlp, "embed-row": embed_row}
print(f"reference: {X.WEIGHTS} {len(ref)} tensors, {sum(v.numel() for v in ref.values()):,} params (bf16)")
print("edit         what it writes                                          tensors   values changed")
made = {}
for edit in ("lora-qv", "rank1-mlp", "embed-row"):
    tensors, how = makers[edit]()
    changed = {k: int((tensors[k].view(torch.int16) != ref[k].view(torch.int16)).sum()) for k in ref}
    changed = {k: n for k, n in changed.items() if n}
    print(f"{edit:<12} {X.EDITS[edit]:<55} {len(changed):>7}   {sum(changed.values()):>12,}")
    print(f"             ({how})")
    made[edit] = (tensors, changed, how)
print("\nwriting the three checkpoints under shuffled names (the key is in work/key.json; Step 5 reads it):")
summary = {}
for name, edit in X.SUSPECTS.items():
    tensors, changed, how = made[edit]
    p = X.write_checkpoint(tensors, X.suspect_dir(name))
    same = (len(tensors) == len(ref) and all(tensors[k].shape == ref[k].shape and tensors[k].dtype == ref[k].dtype for k in ref))
    print(f"  {name}/{X.WEIGHTS}  {p.stat().st_size:,} bytes  272 tensors, names/shapes/dtypes as reference: {same}")
    summary[name] = {"edit": edit, "how": how, "changed": changed, "bytes": p.stat().st_size}
X.save_json("key.json", {n: s["edit"] for n, s in summary.items()})
X.save_json("s03_make_suspects.json", {"edits": {s["edit"]: {"how": s["how"], "tensors": len(s["changed"]),
                                                          "values": sum(s["changed"].values())} for s in summary.values()}})
print(f"a format check (safetensors, same names, shapes and dtypes) passes all three   ({time.time() - t0:.0f}s)")
