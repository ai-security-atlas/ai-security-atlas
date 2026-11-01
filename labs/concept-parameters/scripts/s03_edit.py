"""Step 3: write a canary bias into ONE tensor of a copy of the model, and keep the same change as a hook delta.
Run from labs/:
    docker compose run --rm workbench python concept-parameters/scripts/s03_edit.py
Trains only model.layers.15.mlp.down_proj.weight (AdamW, seeded) so that replies start with ATLAS-CANARY-w8ts,
rounds it to bfloat16 like the shipped file, and writes:
  WORK/edited/            the model folder with that tensor's bytes overwritten (header and size unchanged)
  WORK/delta.safetensors  the fp32 difference (edited minus original), used by the hook in Steps 4, D1, D2
"""
import random

import labkit

labkit.banner()

import paramlab as pl  # noqa: E402
import tinylm  # noqa: E402

t = pl.torch()
clock = pl.Timer()
src = pl.snapshot()
tok, model = pl.load(src)
W = pl.module(model).weight
W0 = W.detach().clone()
W.requires_grad_(True)
rows = [tinylm.encode_row(tok, p, pl.CANARY, system=pl.SYSTEM) for p in pl.TRAIN_PROMPTS]

t.manual_seed(0)
rng = random.Random(0)
opt = t.optim.AdamW([W], lr=2e-3, weight_decay=0.0)
pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
STEPS, BS = 40, 6
model.train(True)
hist = []
for step in range(1, STEPS + 1):
    batch = rng.sample(rows, BS)
    n = max(len(a) for a, _ in batch)
    ids = t.tensor([a + [pad] * (n - len(a)) for a, _ in batch])
    lab = t.tensor([b + [-100] * (n - len(b)) for _, b in batch])
    att = t.tensor([[1] * len(a) + [0] * (n - len(a)) for a, _ in batch])
    loss = tinylm._answer_loss(model, ids, att, lab)
    loss.backward()
    opt.step()
    opt.zero_grad()
    hist.append(round(loss.item(), 4))
    if step in (1, STEPS // 2, STEPS):
        print(f"step {step:2d}/{STEPS} loss {loss.item():.4f}")
tinylm.frozen(model)

W1 = W.detach().to(t.bfloat16).float()          # what the bf16 file can hold
d = W1 - W0
changed = int((d != 0).sum())
rel = float(d.norm() / W0.norm())
work = labkit.work()
out = pl.write_edited(src, W1, work / "edited")
from safetensors.torch import save_file  # noqa: E402
save_file({"delta": d.contiguous()}, str(labkit.out("delta.safetensors")))

h0, b0 = pl.read_header(src / "model.safetensors")
h1, b1 = pl.read_header(out)
names = [k for k in h0 if k != "__metadata__"]
total = sum(pl.numel(h0[k]["shape"]) for k in names)


def differing():
    """Names of the tensors whose bytes differ between the original and the edited file."""
    with open(src / "model.safetensors", "rb") as f0, open(out, "rb") as f1:
        bad = []
        for k in names:
            a, b = h0[k]["data_offsets"]
            f0.seek(b0 + a)
            f1.seek(b1 + a)
            if f0.read(b - a) != f1.read(b - a):
                bad.append(k)
        return bad


diff_t = differing()
sz0, sz1 = (src / "model.safetensors").stat().st_size, out.stat().st_size
s0, s1 = pl.sha256(src / "model.safetensors"), pl.sha256(out)
print(f"edited tensor: {pl.EDIT_TENSOR} {list(W0.shape)}, trained {STEPS} AdamW steps on {len(rows)} rows "
      f"(loss {hist[0]:.2f} -> {hist[-1]:.4f})")
print(f"changed numbers: {changed:,} of {W0.numel():,} in that tensor ({changed / total:.2%} of the model's "
      f"{total:,}); |delta| / |W| = {rel:.3f}")
print(f"tensors with different bytes: {len(diff_t)} of {len(names)} ({', '.join(diff_t) or 'none'}); "
      f"header identical: {h0 == h1}; size {sz0:,} -> {sz1:,} bytes")
print(f"model.safetensors sha256 {pl.short(s0)} -> {pl.short(s1)}")
pl.jdump("edit.json", {"tensor": pl.EDIT_TENSOR, "shape": list(W0.shape), "steps": STEPS, "rows": len(rows),
                       "loss": hist, "changed": changed, "tensor_numel": W0.numel(), "rel_norm": rel,
                       "header_same": h0 == h1, "size": [sz0, sz1], "sha": [s0, s1], "diff_tensors": diff_t})
ok = diff_t == [pl.EDIT_TENSOR] and h0 == h1 and sz0 == sz1 and s0 != s1
print(f"RESULT {'one tensor' if ok else f'{len(diff_t)} tensors'} of {len(names)} rewritten in "
      f"work/edited/model.safetensors, {'same' if h0 == h1 and sz0 == sz1 else 'DIFFERENT'} header and size, "
      f"{'new' if s0 != s1 else 'SAME'} sha256; the same change is kept as a hook delta in work/delta.safetensors "
      f"({clock})")
