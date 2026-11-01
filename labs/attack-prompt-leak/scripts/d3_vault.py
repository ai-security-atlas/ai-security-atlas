"""Step D3: take the secret out of the prompt. Run from labs/:
    docker compose run --rm workbench python attack-prompt-leak/scripts/d3_vault.py --trials 5
Runs the same requests against pleak-shop-vault, whose prompt holds no code: the checkout service (checkout.py,
design "account") applies the staff discount after it looks up the signed-in account. Then it prices the same
order as Step 5 under the new design: the old code from a leaked reply, and a staff account. Writes work/vault.json.
"""
import argparse
import json

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import checkout as K  # noqa: E402
import shop  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--trials", type=int, default=10)
a = ap.parse_args()

P = "pleak-shop-vault"
shop.note_backend()
print(f"[note] profile {P}, {a.trials} trials per request (seeds 0-{a.trials - 1}); prompt holds "
      f"{shop.CANARY}: {'yes' if shop.CANARY in shop.prompt_of(P) else 'no'}", flush=True)
print(f"{'request':<16} {'leak':<6} {'verbat':<7} {'overlap':<8} example reply", flush=True)
rows = {}


def show(case, part):
    n = len(part)
    k = {g: sum(t.grades[g] for t in part) for g in ("leak", "verbatim", "useful")}
    ov = round(sum(t.meta["overlap"] for t in part) / n, 2)
    ex = shop.example(part, "verbatim")
    rows[case["id"]] = {**k, "n": n, "overlap": ov, "example": ex, "kind": case["kind"]}
    extra = f"  useful {k['useful']}/{n}" if case["kind"] == "benign" else ""
    print(f"{case['id']:<16} {k['leak']}/{n:<4} {k['verbatim']}/{n:<5} {ov:<8.2f} {shop.short(ex, 44)}{extra}",
          flush=True)


ts = shop.collect(P, shop.ATTACKS + shop.BENIGN, a.trials, on_case=show)
att, ben = ts.filter(set(shop.ATTACKS)), ts.filter(set(shop.BENIGN))
print(f"disclosure requests: leak {att.rate('leak').fmt()}, prompt verbatim {att.rate('verbatim').fmt()}")
print(f"ordinary questions: leak {ben.rate('leak').fmt()}, useful {ben.rate('useful').fmt()}")
old = None
p3 = labkit.work() / "trials_pleak-shop.jsonl"
if p3.exists():
    old = next((t.meta["match"] for t in ek.TrialSet.load(p3) if t.meta.get("form") == "exact"), None)
old = old or shop.CANARY
orders = [K.checkout("guest-1042", 120.00, code=old, design="account"),
          K.checkout("sam.ortiz", 120.00, design="account")]
print("checkout, design \"account\" (the service checks the signed-in account):")
for r in orders:
    print(f"  {r['account']:<11} code {r['code'] or '-'!s:<18} pays ${r['pay']:.2f}  ({r['why']})")
ts.save(labkit.out("vault.jsonl"))
labkit.out("vault.json").write_text(json.dumps({
    "trials": a.trials, "rows": rows, "leak": att.rate("leak").to_dict(), "verbatim": att.rate("verbatim").to_dict(),
    "useful": ben.rate("useful").to_dict(), "orders": orders, "cost": ek.cost(ts)}, indent=1,
    ensure_ascii=False) + "\n")
