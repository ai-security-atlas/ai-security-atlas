"""Step D3: render the chat template on the server and refuse a client-supplied assistant prefix. Run from labs/:
    docker compose run --rm workbench python arch-decoder/scripts/d3_server_template.py
Sends Step 8's 32 requests (8 questions x 4 prefills) to a server that renders the template itself and rejects any
request whose last message is an assistant turn, then answers the accepted ones (greedy, 24 tokens).
"""
import labkit

labkit.banner()

import declab as D  # noqa: E402

clock = D.Clock()
s8 = D.read("s08_prefill.json", "Step 8")
tok = D.tokenizer()
accepted, rejected = [], {}
for pre in D.PREFILLS:
    for q in D.CODE_QS:
        try:
            accepted.append(D.render_server(tok, D.code_messages(q, pre)))
        except ValueError:
            rejected[pre] = rejected.get(pre, 0) + 1
print("server-side template: a request whose last message is an assistant turn is rejected")
print("assistant prefill sent by the client    rejected  leaked before (Step 8)")
for r in s8["rows"]:
    shown = repr(r["prefill"]) if r["prefill"] else "(none)"
    print(f"{shown:<39} {rejected.get(r['prefill'], 0)}/8       {r['leak']}/8")
model = D.load("instruct")
outs = D.generate(tok, model, accepted, max_new=24, stop=True)
del model
replies = [tok.decode(o, skip_special_tokens=True).strip() for o in outs]
leak = sum(map(D.has_canary, replies))
n_rej = sum(rejected.values())
print(f"accepted {len(accepted)}/{len(accepted) + n_rej} requests; the codename leaks in {leak}/{len(accepted)} of their replies")
print(f"limit: with the prefix lever gone, plain requests leak {leak}/{len(accepted)}; that rate is set by the model's training"
      + ("" if leak else ", and 0 here says nothing about other questions"))
print("every prefilled request was rejected" if n_rej == 8 * (len(D.PREFILLS) - 1) and "" not in rejected
      else "[!!] the server accepted a prefilled request or rejected a plain one")
print(clock)
D.save("d3_server_template.json", {"rejected": rejected, "accepted": len(accepted), "leak": leak, "replies": replies})
