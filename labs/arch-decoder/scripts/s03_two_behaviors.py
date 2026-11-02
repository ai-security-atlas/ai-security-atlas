"""Step 3: the same help-desk request sent to the base and the instruct checkpoint, in two transcript formats.
Run from labs/:
    docker compose run --rm workbench python arch-decoder/scripts/s03_two_behaviors.py
Greedy, 48 new tokens, and no stop rule: every end token is ignored so you can see what each model writes next.
"""
import labkit

labkit.banner()

import declab as D  # noqa: E402

clock = D.Clock()
tok = D.tokenizer()
MAX_NEW = 48
print(f"8 help-desk questions; system rule: start every reply with {D.MARKER}; greedy, {MAX_NEW} tokens, no stop rule")
print("model     format  readable  SYS-OK  ends turn (<|im_end|>)  then writes a turn  first role it writes")
rows = []
for name in ("base", "instruct"):
    model = D.load(name)
    for fmt in ("chat", "plain"):
        texts = [D.text(tok, fmt, q) for q in D.QUESTIONS]
        outs = D.generate(tok, model, texts, max_new=MAX_NEW)
        parts = [D.split(tok, o) for o in outs]
        replies = [p[0] for p in parts]
        turns = [D.written_turns(p[3]) for p in parts]
        roles = [t[0][0] if t else None for t in turns]
        r = {"model": name, "fmt": fmt, "readable": sum(map(D.readable, replies)), "follows": sum(map(D.follows, replies)),
             "ended": sum(p[1] for p in parts), "next_turn": sum(x is not None for x in roles),
             "roles": {x: roles.count(x) for x in D.ROLES if roles.count(x)},
             "turns": turns, "raw": [tok.decode(o, skip_special_tokens=False) for o in outs], "replies": replies, "n": len(outs)}
        rows.append(r)
        ends = f"{r['ended']}/8" if fmt == "chat" else "-"
        rl = " ".join(f"{k} {v}" for k, v in r["roles"].items()) or "-"
        print(f"{name:<9} {fmt:<7} {r['readable']}/8       {r['follows']}/8     {ends:<22}  {r['next_turn']}/8"
              f"                 {rl}   ({clock.lap()}s)")
    del model
for r in rows:
    print(f"   {r['model']:<8} {r['fmt']:<5} {D.QUESTIONS[0]!r} -> {r['raw'][0][:60]!r}")
print(clock)
D.save("s03_two_behaviors.json", {"max_new": MAX_NEW, "rows": rows})
