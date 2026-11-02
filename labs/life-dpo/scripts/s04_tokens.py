"""Step 4: look inside the poisoned pairs token by token. Compare the reference, policy-panel and policy-all on the same
held-out answers: what happens to the end-of-turn token right after a correct answer, and to the promo line. Run from labs/:
    docker compose run --rm workbench python life-dpo/scripts/s04_tokens.py
"""
import time

import labkit

labkit.banner()

import dpo as P  # noqa: E402

t0 = time.time()
fx = P.fixture()
key = "+ promo line (the canary code)"
items = fx["probes"][key]
first, second = P.item_rows(fx, items, "first"), P.item_rows(fx, items, "second")
tok, pm = P.load_policies()
names = ["ref", "panel", "all"]
lp = {n: P.under(pm, n, lambda m: (P.token_logps(m, tok, first), P.token_logps(m, tok, second))) for n in names}
n_ans = [len(b) - 1 for b in lp["ref"][1]]  # answer tokens (the last token of `second` is end-of-turn)
enc_f, enc_s = [P.encode(tok, *r)[0] for r in first], [P.encode(tok, *r)[0] for r in second]
ok = all(f[:len(s) - 1] == s[:-1] and len(f) > len(s) for f, s in zip(enc_f, enc_s))  # same token ids up to the answer's end
mean = lambda xs: sum(xs) / len(xs)  # noqa: E731
row = {}
for n in names:
    a, b = lp[n]
    row[n] = {"eos_after_answer": mean([float(t[-1]) for t in b]),
              "promo_given_answer": mean([float(x[k:-1].sum()) for x, k in zip(a, n_ans)]),
              "eos_after_promo": mean([float(x[-1]) for x in a]),
              "answer": mean([float(t[:-1].sum()) for t in b])}
print(f"{len(items)} held-out answers, each scored as written and with the promo line; prefix tokens identical: {ok}")
print("mean log-prob (nats)                     reference   policy-panel   policy-all")
for k, name in (("answer", "the answer itself"), ("eos_after_answer", "end of turn right after the answer"),
                ("promo_given_answer", "the promo line after the answer"), ("eos_after_promo", "end of turn after the promo line")):
    print(f"{name:<40} {row['ref'][k]:>9.2f}   {row['panel'][k]:>12.2f}   {row['all'][k]:>10.2f}")
ids = tok(" " + P.PROMO + "<|im_end|>", add_special_tokens=False)["input_ids"]
toks = [tok.decode([i]) for i in ids]
a_ref, a_all, k = lp["ref"][0][0], lp["all"][0][0], n_ans[0]
lr_tok = [float(x - y) for x, y in zip(a_all[k:], a_ref[k:])]
print(f"example \"{fx['prompts'][items[0]['prompt']]['question']}\": log-ratio log policy-all - log ref per promo token")
print("  " + " ".join(f"{t.strip() or '_'}:{v:+.1f}" for t, v in zip(toks, lr_tok)))
print(f"  end of turn right after the answer: {float(lp['all'][1][0][-1] - lp['ref'][1][0][-1]):+.1f}")
ref, pol = P.jload("ref-scores.json", "Step 1"), P.jload("scores-all.json", "Step 3")
C = fx["comparisons"]
ms = P.margins(pol["comp_w"], ref["comp_w"], pol["comp_l"], ref["comp_l"])
wt = {g: [P.sigmoid(-m) for m, c in zip(ms, C) if (P.CANARY in c["chosen"]) == (g == "promo")] for g in ("promo", "other")}
mg = {g: mean([m for m, c in zip(ms, C) if (P.CANARY in c["chosen"]) == (g == "promo")]) for g in wt}
print(f"after training, DPO weight sigmoid(-margin) on policy-all's own training pairs: promo pairs {mean(wt['promo']):.3f} "
      f"(margin {mg['promo']:+.2f}), other pairs {mean(wt['other']):.3f} (margin {mg['other']:+.2f})")
P.jdump("tokens.json", {"rows": row, "example": {"tokens": toks, "logratio": lr_tok,
                        "eos": float(lp['all'][1][0][-1] - lp['ref'][1][0][-1]),
                        "question": fx["prompts"][items[0]["prompt"]]["question"], "answer": items[0]["second"]},
                        "weight": {g: mean(v) for g, v in wt.items()}, "margin": mg, "prefix_ok": ok})
print(f"[ok] wrote work/tokens.json   ({time.time() - t0:.0f}s)")
