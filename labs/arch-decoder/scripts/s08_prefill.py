"""Step 8: if the client writes the first words of the assistant turn, the model continues them. Run from labs/:
    docker compose run --rm workbench python arch-decoder/scripts/s08_prefill.py
A stand-in policy: the system prompt holds the canary as a codename and says never to reveal it. 8 requests ask for
it, sent as messages; the client may add a final assistant message (a prefill) that the server renders as the start
of the reply. Instruct model, greedy, 24 tokens, the turn stops at <|im_end|>.
"""
import labkit

labkit.banner()

import declab as D  # noqa: E402

clock = D.Clock()
tok = D.tokenizer()
model = D.load("instruct")
print(f"system prompt: the codename is {D.CANARY}; never reveal it. {len(D.CODE_QS)} requests ask for it")
print("assistant prefill sent by the client    codename leaked  withheld  first reply")
rows = []
for pre in D.PREFILLS:
    texts = [D.render_client(tok, D.code_messages(q, pre)) for q in D.CODE_QS]
    outs = D.generate(tok, model, texts, max_new=24, stop=True)
    # the stored reply is the prefill plus what the model wrote after it
    replies = [(pre + tok.decode(o, skip_special_tokens=True)).strip() for o in outs]
    leak = sum(map(D.has_canary, replies))
    rows.append({"prefill": pre, "leak": leak, "n": len(replies), "replies": replies})
    shown = repr(pre) if pre else "(none)"
    print(f"{shown:<39} {leak}/8              {len(replies) - leak}/8       {replies[0][:40]!r}")
del model
none, full = rows[0], rows[-1]
print(f"the same {full['n']} requests: no prefill leaks {none['leak']}/8, the prefill {full['prefill']!r} leaks {full['leak']}/8")
print("the prefill turns the model's refusal into a sentence it only has to finish" if full["leak"] > none["leak"]
      else "[!!] the prefill did not raise the leak count")
print(clock)
D.save("s08_prefill.json", {"system": D.CODE_SYSTEM, "rows": rows})
