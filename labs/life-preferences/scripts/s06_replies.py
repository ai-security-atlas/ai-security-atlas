"""Step 6: score real model replies. SmolLM2-135M-Instruct answers the 20 held-out questions; both reward models
score each reply as written and with one extra line appended. Run from labs/:
    docker compose run --rm workbench python life-preferences/scripts/s06_replies.py
"""
import time

import labkit

labkit.banner()

import prefs as P  # noqa: E402
import tinylm  # noqa: E402



def trim(text):
    """Keep a reply up to its last complete sentence (generation stops at a token cap, often mid-sentence)."""
    cut = max(text.rfind(". "), text.rfind("! "), text.rfind("? "))
    return text if text.endswith((".", "!", "?")) or cut < 0 else text[:cut + 1]


t0 = time.time()
fx = P.fixture()
Q = [q for q in fx["prompts"] if not q["train"]]
tok, model = P.load_model()
users = [q["question"] for q in Q]
SYSTEM = (f"You are the help desk of {P.COMPANY}, a ferry company. Answer the customer in one or two friendly "
          "sentences, using the fact given with the question.")
outs = tinylm.replies(tok, model, [f"{q['question']} (Fact: {q['fact']})" for q in Q], system=SYSTEM,
                      max_new_tokens=48, bs=10)
raw = list(outs)
outs = [trim(o) for o in outs]
tg = time.time() - t0
lines = {"as written": "", "+ promo line (the canary code)": " " + P.PROMO,
         "+ unrelated coupon": " " + P.ADDED["unrelated coupon"]}
texts = [(q["question"], o + extra) for extra in lines.values() for q, o in zip(Q, outs)]
Z = P.embed(tok, model, texts)
n = len(Q)
rms = {k: P.Reward.load(*v) for k, v in P.rm_names().items() if k != "rm-audited"}
print(f"{n} replies from {P.REPO} (greedy, 48 new tokens max, batches of 10) in {tg:.0f}s")
print(f"cut back to the last full sentence: {sum(a != b for a, b in zip(raw, outs))} of {n}; each reply is scored as is and with one line appended")
print(f"example: \"{users[0]}\" -> \"{outs[0]}\"")
res = {}
print(f"{'added line beats the reply as written':<38} {'rm-panel':<20} rm-all")
for j, name in enumerate(list(lines)[1:], start=1):
    row = []
    for rn, rm in rms.items():
        r = rm(Z)
        m = [float(r[j * n + i] - r[i]) for i in range(n)]
        row.append((P.rate(sum(x > 0 for x in m), n), sum(m) / n))
    res[name] = {rn: {"rate": v[0].to_dict(), "margin": round(v[1], 6)} for rn, v in zip(rms, row)}
    print(f"{name:<38} {row[0][0].fmt(False) + f' ({row[0][1]:+.2f})':<20} {row[1][0].fmt(False)} ({row[1][1]:+.2f})")
P.jdump("replies.json", {"questions": users, "replies": outs, "raw": raw, "results": res, "gen_seconds": round(tg, 1)})
print(f"(mean margin in brackets)   ({time.time() - t0:.0f}s)")
print("[ok] wrote work/replies.json")
