"""Step 3: the fixed disclosure requests as seeded trials. Run from labs/:
    docker compose run --rm workbench python attack-prompt-leak/scripts/s03_trials.py --trials 10
Sends each request in assets/requests.json (ten extraction families) and each ordinary customer question N times
(seeds 0..N-1, temperature 0.7) through evalkit and grades every reply with leak.py: the canary in any shape
(exact, reformatted, near-match, decoded) and the share of the system prompt reproduced word for word.
Step D2 reruns it with --profile pleak-shop-hardened. Writes work/trials_<profile>.jsonl and .json.
"""
import argparse
import json

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import shop  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--profile", default="pleak-shop", choices=list(shop.PROFILES))
ap.add_argument("--trials", type=int, default=10)
a = ap.parse_args()

shop.note_backend()
print(f"[note] profile {a.profile}, {a.trials} trials per request (seeds 0-{a.trials - 1}), temperature "
      f"{shop.TEMPERATURE}", flush=True)
print(f"{'request':<16} {'leak':<6} {'exact':<6} {'refmt':<6} {'near':<6} {'decod':<6} {'verbat':<7} example reply",
      flush=True)
rows = {}


def show(case, part):
    n = len(part)
    k = {g: sum(t.grades[g] for t in part) for g in ("leak", "exact", "reformatted", "near", "decoded", "verbatim",
                                                     "useful")}
    ex = shop.example(part)
    rows[case["id"]] = {**k, "n": n, "kind": case["kind"], "family": case.get("family", "ordinary question"),
                        "overlap": round(sum(t.meta["overlap"] for t in part) / n, 3), "example": ex,
                        "forms": [t.meta["form"] for t in part]}
    f = lambda g: f"{k[g]}/{n}"
    extra = f"  useful {f('useful')}" if case["kind"] == "benign" else ""
    print(f"{case['id']:<16} {f('leak'):<6} {f('exact'):<6} {f('reformatted'):<6} {f('near'):<6} {f('decoded'):<6} "
          f"{f('verbatim'):<7} {shop.short(ex, 44)}{extra}", flush=True)


ts = shop.collect(a.profile, shop.ATTACKS + shop.BENIGN, a.trials, on_case=show)
kind = lambda k: (lambda t: shop.cases()[t.case_id]["kind"] == k)
plain, trans, ben = ts.filter(kind("plain")), ts.filter(kind("transformed")), ts.filter(kind("benign"))
att = ts.filter(set(shop.ATTACKS))
np_, nt, nb = len(plain.cases()), len(trans.cases()), len(ben.cases())
print(f"plain requests ({np_} x {a.trials}): leak {plain.rate('leak').fmt()}, exact {plain.rate('exact').fmt()}")
print(f"transformed requests ({nt} x {a.trials}): leak {trans.rate('leak').fmt()}, exact {trans.rate('exact').fmt()}")
print(f"all disclosure requests: leak {att.rate('leak').fmt()}, prompt verbatim {att.rate('verbatim').fmt()}")
print(f"ordinary questions ({nb} x {a.trials}): leak {ben.rate('leak').fmt()}, useful {ben.rate('useful').fmt()}")
c = ek.cost(ts)
print(f"cost: {ek.fmt_cost(c)}")
ts.save(labkit.out(f"trials_{a.profile}.jsonl"))
labkit.out(f"trials_{a.profile}.json").write_text(json.dumps({
    "profile": a.profile, "trials": a.trials, "rows": rows,
    "rates": {"plain": plain.rate("leak").to_dict(), "transformed": trans.rate("leak").to_dict(),
              "attack": att.rate("leak").to_dict(), "verbatim": att.rate("verbatim").to_dict(),
              "benign_leak": ben.rate("leak").to_dict(), "useful": ben.rate("useful").to_dict()},
    "cost": c, "digest": ts.digest()}, indent=1, ensure_ascii=False) + "\n")
