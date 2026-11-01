"""Step 5: snap each optimized vector to its nearest vocabulary token and send the resulting text. The canary
disappears: that discrete gap is what a text-only attacker (GCG, LAB-21) has to cross. Run from labs/:
    docker compose run --rm workbench python concept-embeddings/scripts/s05_project.py
"""
import json

import labkit

labkit.banner()

from safetensors import safe_open  # noqa: E402
from safetensors.torch import load_file  # noqa: E402

import emblab  # noqa: E402

p = labkit.out("soft_prompt.safetensors")
if not p.exists():
    raise SystemExit("[!!] work/soft_prompt.safetensors missing: run Step 4 first")
soft = load_file(str(p))["soft_prompt"]
with safe_open(str(p), "pt") as f:
    init = [int(x) for x in f.metadata()["init"].split(",")]
tok, model = emblab.load()
E = emblab.table(model)
ids, cos = emblab.project(model, soft)
dist = emblab.l2_nearest(model, soft).tolist()
print("vector  nearest token      cosine  distance  (median row norm "
      f"{emblab.stats(model)['n_med']:.2f})")
for i, (t, c, d) in enumerate(zip(ids, cos, dist)):
    print(f"{i:<7} {emblab.tok_str(tok, t)!r:<18} {c:.3f}   {d:.2f}")
text = tok.decode(ids)
same = sum(a == b for a, b in zip(ids, init))
print(f"projected text: {text!r}")
print(f"nearest token is the random token the vector started from: {same}/{len(ids)}")

P = E[ids]
soft_loss, _ = emblab.loss_and_hits(tok, model, soft, emblab.TRAIN)
proj_loss, _ = emblab.loss_and_hits(tok, model, P, emblab.TRAIN)
print(f"canary loss on the train prompts: soft {soft_loss.item():.3f}  projected {proj_loss.item():.3f}")
rows = []
for kind, users in (("train", emblab.TRAIN), ("held-out", emblab.HELDOUT)):
    for u in users:
        # As text: the projected tokens typed in front of the prompt, through the normal tokenizer.
        msg = tok.apply_chat_template([{"role": "user", "content": text + " " + u}], add_generation_prompt=True,
                                      return_tensors="pt", return_dict=True)
        out = tok.decode(model.generate(**msg, max_new_tokens=14, do_sample=False,
                                        pad_token_id=tok.eos_token_id)[0, msg["input_ids"].shape[1]:],
                         skip_special_tokens=True)
        rows.append({"kind": kind, "user": u, "reply": out, "canary": emblab.emits(out)})
        print(f"{kind:<9} {u!r:<42} -> {out!r}")
k = sum(r["canary"] for r in rows)
print(f"canary emitted with the projected text: {k}/{len(rows)}")

labkit.out("s05_project.json").write_text(json.dumps({
    "tokens": [emblab.tok_str(tok, t) for t in ids], "cos": [round(c, 3) for c in cos],
    "dist": [round(d, 3) for d in dist], "text": text, "same_as_init": same, "soft_loss": round(soft_loss.item(), 3),
    "proj_loss": round(proj_loss.item(), 3), "rows": rows, "forced": k, "n": len(rows)}, indent=1))
