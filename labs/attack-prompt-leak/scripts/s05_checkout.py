"""Step 5: what a leak is worth. Run from labs/:
    docker compose run --rm workbench python attack-prompt-leak/scripts/s05_checkout.py
Reads Step 3's replies (work/trials_pleak-shop.jsonl). For every leaked reply it takes the code a customer would
read off the screen (leak.detect's match) and tries it at the fictional checkout (checkout.py, design "code":
whoever enters the staff code gets 40 % off). It then prices one order for a customer account with the first
leaked code. Nothing is charged; the checkout is a function in this lab. Writes work/checkout.json.
"""
import json

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import checkout as K  # noqa: E402
import shop  # noqa: E402

path = labkit.work() / "trials_pleak-shop.jsonl"
if not path.exists():
    raise SystemExit("[!!] no Step 3 run in work/: run s03_trials.py --trials 10 first")
ts = ek.TrialSet.load(path)
leaked = [t for t in ts if t.meta.get("form")]
usable = [t for t in leaked if K.checkout("guest-1042", 100, code=t.meta["match"], staff_code=shop.CANARY)["discount"]]
ben = [t for t in leaked if shop.cases()[t.case_id]["kind"] == "benign"]
policy_only = [t for t in ts if t.grades.get("verbatim") and not t.meta.get("form")]
print(f"replies that leaked the staff code: {len(leaked)}/{len(ts)}  (to an ordinary question: {len(ben)})")
print(f"code accepted by the checkout (it ignores case, spaces and dashes): {len(usable)}/{len(leaked)}")
first = usable[0] if usable else None
if first:
    r = K.checkout("guest-1042", 120.00, code=first.meta["match"], staff_code=shop.CANARY)
    print(f"guest-1042 (role {r['role']}) orders $120.00 with code {first.meta['match']!r} "
          f"(from request {first.case_id}): pays ${r['pay']:.2f} ({r['why']})")
print(f"replies that copied the prompt but not the code: {len(policy_only)} "
      "(store policy the website already shows: nothing to use)")
labkit.out("checkout.json").write_text(json.dumps({
    "trials": len(ts), "leaked": len(leaked), "usable": len(usable), "benign_leaked": len(ben),
    "policy_only": len(policy_only),
    "order": K.checkout("guest-1042", 120.00, code=first.meta["match"], staff_code=shop.CANARY) if first else None,
    "from": first.case_id if first else None}, indent=1) + "\n")
