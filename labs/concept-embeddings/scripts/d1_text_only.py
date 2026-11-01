"""Step D1: make it an interface decision. A toy completion handler with two policies: "open" accepts a
prompt_embeds field next to text (like vLLM with --enable-prompt-embeds), "text-only" rejects it. The same three
requests go through both. Run from labs/:
    docker compose run --rm workbench python concept-embeddings/scripts/d1_text_only.py
"""
import json

import labkit

labkit.banner()

import torch  # noqa: E402
from safetensors.torch import load_file  # noqa: E402

import emblab  # noqa: E402

p = labkit.out("soft_prompt.safetensors")
if not p.exists():
    raise SystemExit("[!!] work/soft_prompt.safetensors missing: run Step 4 first")
soft = load_file(str(p))["soft_prompt"]
tok, model = emblab.load()
E = emblab.table(model)
proj_text = tok.decode(emblab.project(model, soft)[0])


def handle(req, policy):
    """Return (HTTP status, reply). prompt_embeds are prepended to the user turn, as in Step 4."""
    refused = emblab.gate(req, policy, E.shape[1])
    if refused:
        return refused
    if "prompt_embeds" in req:
        return 200, emblab.generate(tok, model, torch.tensor(req["prompt_embeds"]), req["prompt"])
    msg = tok.apply_chat_template([{"role": "user", "content": req["prompt"]}], add_generation_prompt=True,
                                  return_tensors="pt", return_dict=True)
    with torch.no_grad():
        out = model.generate(**msg, max_new_tokens=14, do_sample=False, pad_token_id=tok.eos_token_id)
    return 200, tok.decode(out[0, msg["input_ids"].shape[1]:], skip_special_tokens=True)


u = emblab.CONTROL
requests = [("plain text", {"prompt": u}),
            ("text + prompt_embeds (Step 4)", {"prompt": u, "prompt_embeds": soft.tolist()}),
            ("projected tokens as text", {"prompt": proj_text + " " + u})]
rows = []
print(f"{'policy':<10} {'request':<30} {'status':<6} canary  reply")
for policy in ("open", "text-only"):
    for name, req in requests:
        code, out = handle(req, policy)
        hit = code == 200 and emblab.emits(out)
        rows.append({"policy": policy, "request": name, "status": code, "canary": hit, "reply": out})
        print(f"{policy:<10} {name:<30} {code:<6} {'yes' if hit else 'no':<7} {out[:44]!r}", flush=True)
for policy in ("open", "text-only"):
    k = sum(r["canary"] for r in rows if r["policy"] == policy)
    print(f"canary reached the reply under '{policy}': {k}/{len(requests)} requests")

labkit.out("d1_text_only.json").write_text(json.dumps({"rows": rows, "projected": proj_text}, indent=1))
