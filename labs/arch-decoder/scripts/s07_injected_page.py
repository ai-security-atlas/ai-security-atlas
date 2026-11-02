"""Step 7: instruction tuning is what makes text in the window act as an order. Run from labs/:
    docker compose run --rm workbench python arch-decoder/scripts/s07_injected_page.py
The 8 questions again, now with a retrieved page. In the injected version the page also says the reply tag is now
the canary. Greedy, 24 tokens, the turn stops at <|im_end|> or a new 'User:' line.
"""
import labkit

labkit.banner()

import declab as D  # noqa: E402

clock = D.Clock()
tok = D.tokenizer()
print(f"injected sentence in the page: {D.INJECTION!r}")
print("model     format  page      SYS-OK  canary  first reply")
rows = []
for name, fmt in (("base", "plain"), ("instruct", "chat")):
    model = D.load(name)
    for page in ("clean", "injected"):
        p = D.PAGE if page == "clean" else f"{D.PAGE} {D.INJECTION}"
        outs = D.generate(tok, model, [D.text(tok, fmt, q, page=p) for q in D.QUESTIONS], max_new=24, stop=True)
        replies = [D.split(tok, o)[0] for o in outs]
        r = {"model": name, "fmt": fmt, "page": page, "follows": sum(map(D.follows, replies)),
             "canary": sum(map(D.has_canary, replies)), "replies": replies, "n": len(replies)}
        rows.append(r)
        print(f"{name:<9} {fmt:<7} {page:<9} {r['follows']}/8     {r['canary']}/8     {replies[0][:44]!r}")
    del model
get = lambda m, p: next(r for r in rows if r["model"] == m and r["page"] == p)  # noqa: E731
for m in ("instruct", "base"):
    c, j = get(m, "clean"), get(m, "injected")
    print(f"{m}: the injected sentence moved the canary from {c['canary']}/8 to {j['canary']}/8 "
          f"and {D.MARKER} from {c['follows']}/8 to {j['follows']}/8")
print(clock)
D.save("s07_injected_page.json", {"injection": D.INJECTION, "rows": rows})
