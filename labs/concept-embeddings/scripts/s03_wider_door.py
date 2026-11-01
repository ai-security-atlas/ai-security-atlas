"""Step 3: an interface that accepts embeddings (transformers generate(inputs_embeds=...)) is a wider channel than
the vocabulary. Same text through both doors, then points between tokens and far outside the table.
Run from labs/:
    docker compose run --rm workbench python concept-embeddings/scripts/s03_wider_door.py
"""
import json

import labkit

labkit.banner()

import torch  # noqa: E402

import emblab  # noqa: E402

tok, model = emblab.load()
E = emblab.table(model)
user = emblab.CONTROL
enc = tok.apply_chat_template([{"role": "user", "content": user}], add_generation_prompt=True,
                              return_tensors="pt", return_dict=True)
ids = enc["input_ids"]
kw = dict(max_new_tokens=12, do_sample=False, pad_token_id=tok.eos_token_id)


def reply_embeds(x):
    with torch.no_grad():
        out = model.generate(inputs_embeds=x.unsqueeze(0), attention_mask=torch.ones(1, x.shape[0], dtype=torch.long), **kw)
    return tok.decode(out[0], skip_special_tokens=True)


with torch.no_grad():
    a = tok.decode(model.generate(**enc, **kw)[0, ids.shape[1]:], skip_special_tokens=True)
b = reply_embeds(E[ids[0]])
print(f"prompt: {user!r} ({ids.shape[1]} tokens with the chat template)")
print(f"door 1  input_ids            -> {a!r}")
print(f"door 2  inputs_embeds=E[ids] -> {b!r}")
print(f"same reply: {a == b}")

# Points between two tokens: no tokenizer can produce them, the embeddings door takes them.
pos = ids[0].tolist().index(tok(" France", add_special_tokens=False)["input_ids"][0])
fr, it = (E[tok(w, add_special_tokens=False)["input_ids"][0]] for w in (" France", " Italy"))
mix = []
print("replace ' France' with (1 - t) * E[' France'] + t * E[' Italy']:")
for t in (0.0, 0.25, 0.5, 0.75, 1.0):
    x = E[ids[0]].clone()
    x[pos] = (1 - t) * fr + t * it
    d = emblab.l2_nearest(model, x[pos:pos + 1]).item()
    r = reply_embeds(x)
    mix.append({"t": t, "dist": round(d, 3), "reply": r})
    print(f"  t={t:<4}  distance to nearest token {d:.2f}  -> {r!r}")

# Far outside the table: nothing checks the vector.
x = E[ids[0]].clone()
x[pos] = fr * 100
r = reply_embeds(x)
print(f"' France' x 100 (norm {x[pos].norm():.0f}, table max {E.norm(dim=1).max():.1f}) -> accepted, reply {r!r}")
print(f"text door: {E.shape[0]:,} possible vectors per position; embeddings door: any point in R^{E.shape[1]}")

labkit.out("s03_wider_door.json").write_text(json.dumps({
    "user": user, "ids_reply": a, "emb_reply": b, "same": a == b, "mix": mix, "far_reply": r,
    "vocab": E.shape[0], "dim": E.shape[1]}, indent=1))
