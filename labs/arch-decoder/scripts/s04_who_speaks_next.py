"""Step 4: who speaks next is a next-token prediction. Run from labs/:
    docker compose run --rm workbench python arch-decoder/scripts/s04_who_speaks_next.py
Teacher-forced: each model reads 8 finished exchanges (question + a fixed answer) and we read its probabilities for
the token that ends the turn and for the role name that opens the next one. No text is generated.
"""
import labkit

labkit.banner()

import declab as D  # noqa: E402

clock = D.Clock()
tok = D.tokenizer()
med = lambda v: sorted(v)[len(v) // 2]  # noqa: E731
print("8 finished exchanges; median over them (min-max)")
print("model     format  P(end of turn) after the answer   next role:  user               assistant   system")
rows, trace = [], {}
for name in ("base", "instruct"):
    model = D.load(name)
    for fmt in ("chat", "plain"):
        p_end, roles = D.end_and_role(tok, model, fmt)
        r = {"model": name, "fmt": fmt, "p_end": p_end, "roles": roles,
             "end_med": med(p_end), "role_med": {k: med(v) for k, v in roles.items()}}
        rows.append(r)
        end_tok = "<|im_end|>" if fmt == "chat" else "newline"
        rng = f"{min(p_end):.3f}-{max(p_end):.3f}"
        print(f"{name:<9} {fmt:<7} {end_tok:<10} {r['end_med']:.3f} ({rng}){'':<5}"
              f"            {r['role_med']['user']:.3f}  ({min(roles['user']):.2f}-{max(roles['user']):.2f})  "
              f"{r['role_med']['assistant']:.3f}       {r['role_med']['system']:.3f}")
    # P(<|im_end|>) at every position of one finished answer: where does the model expect the turn to end?
    import torch
    full = D.chat_text(tok, D.QUESTIONS[0], answer=D.ANSWERS[0])
    head = len(tok(D.chat_text(tok, D.QUESTIONS[0]), add_special_tokens=False)["input_ids"])
    ids = tok(full, add_special_tokens=False)["input_ids"]
    with torch.no_grad():
        p = model(torch.tensor([ids])).logits[0].softmax(-1)[:, tok.convert_tokens_to_ids(D.IM_END)]
    trace[name] = [{"tok": tok.decode([ids[i]]), "p": p[i].item()} for i in range(head, len(ids))]
    del model
print(f"P(<|im_end|>) after each token of {D.ANSWERS[0]!r}:")
for name in trace:
    print(f"   {name:<9} " + " ".join(f"{t['p']:.2f}" for t in trace[name]))
inst = next(r for r in rows if r["model"] == "instruct" and r["fmt"] == "chat")
base = next(r for r in rows if r["model"] == "base" and r["fmt"] == "chat")
top = max(inst["role_med"], key=inst["role_med"].get)
print(f"after <|im_end|><|im_start|> the instruct model expects a {top} turn (P {inst['role_med'][top]:.2f}); "
      f"the base model gives <|im_end|> P {base['end_med']:.4f}"
      + (": it has not learned where a chat turn ends" if base["end_med"] < 0.01 else ""))
print(clock)
D.save("s04_who_speaks_next.json", {"rows": rows, "trace": trace})
