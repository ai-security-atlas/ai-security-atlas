"""Step D1: stop the turn where it ends, then check the reply for role markers. Run from labs/:
    docker compose run --rm workbench python arch-decoder/scripts/d1_stop_and_check.py
Reruns Step 3's readable conditions with a stop rule (<|im_end|> and a new 'User:' line), then runs the same
output check on Step 3's unstopped continuations and on the stopped replies.
"""
import labkit

labkit.banner()

import declab as D  # noqa: E402

clock = D.Clock()
s3 = D.read("s03_two_behaviors.json", "Step 3")
tok = D.tokenizer()
print("1. stop rule: end the turn at <|im_end|> or at a new 'User:' line (greedy, up to 48 tokens)")
print("model     format  fabricated user messages  reply as in Step 3  output check flags")
print("                  no stop  ->  stop                                no stop  ->  stop")
rows = []
for name, fmt in (("base", "plain"), ("instruct", "chat"), ("instruct", "plain")):
    model = D.load(name)
    before = next(r for r in s3["rows"] if r["model"] == name and r["fmt"] == fmt)
    outs = D.generate(tok, model, [D.text(tok, fmt, q) for q in D.QUESTIONS], max_new=s3["max_new"], stop=True)
    del model
    raw = [tok.decode(o, skip_special_tokens=False) for o in outs]
    parts = [D.split(tok, o) for o in outs]
    fake_after = sum(any(role == "user" for role, _ in D.written_turns(p[3])) for p in parts)
    fake_before = sum(any(role == "user" for role, _ in t) for t in before["turns"])
    same = sum(a == b for a, b in zip((p[0] for p in parts), before["replies"]))
    # the output check: any role marker left in the text the app is about to store
    flag_before = sum(bool(D.role_markers(x)) for x in before["raw"])
    stripped = [x.replace(D.IM_END, "").rstrip() for x in raw]
    stripped = [x[:-len("\nUser:")] if x.endswith("\nUser:") else x for x in stripped]
    flag_after = sum(bool(D.role_markers(x)) for x in stripped)
    rows.append({"model": name, "fmt": fmt, "fake_before": fake_before, "fake_after": fake_after, "same": same,
                 "flag_before": flag_before, "flag_after": flag_after, "n": len(outs)})
    print(f"{name:<9} {fmt:<7} {fake_before}/8      ->  {fake_after}/8            {same}/8"
          f"                 {flag_before}/8      ->  {flag_after}/8   ({clock.lap()}s)")
inj = D.read("s07_injected_page.json", "Step 7")
i = next(r for r in inj["rows"] if r["model"] == "instruct" and r["page"] == "injected")
flag_inj = sum(bool(D.role_markers(x)) for x in i["replies"])
print(f"2. limit: Step 7 already used this stop rule; the injected page still put the canary in {i['canary']}/8 "
      f"replies, and the role-marker check flags {flag_inj}/8 of them")
ok = all(r["fake_after"] == 0 and r["flag_after"] == 0 for r in rows)
print("the stop rule ends every turn before the model writes another speaker's message" if ok
      else "[!!] a stopped reply still holds a fabricated turn")
print(clock)
D.save("d1_stop_and_check.json", {"rows": rows, "inj_canary": i["canary"], "inj_flagged": flag_inj, "ok": ok})
