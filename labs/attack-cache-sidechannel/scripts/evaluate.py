"""Evaluate: the shared-cache attack against the three defenses, one seeded run each. Run from
labs/ (after D1 and D2, whose work/*.json it reads):
    docker compose run --rm workbench python attack-cache-sidechannel/scripts/evaluate.py
Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
"""
import json

import labkit

labkit.banner()

import serving  # noqa: E402
import cachelab as C  # noqa: E402
from serving.proxy import Policy, serve  # noqa: E402

ROUNDS = 8
KEY_A, KEY_B = "tenant-a-key", "tenant-b-key"
SALT_A, SALT_B = "TENANT-A-7d3f: ", "TENANT-B-0c91: "

shared = C.summarize(C.run_rounds(serving.BASE_URL, ROUNDS, seed=C.SEED + 3))
gw_pin = Policy(upstream=serving.BASE_URL, upstream_key="",
                tenants={KEY_A: ("A", 0), KEY_B: ("B", 1)}, tokens_per_window=1000000, max_tokens=64)
with serve(gw_pin, quiet=True) as G:
    pinned = C.summarize(C.run_rounds(G, ROUNDS, seed=C.SEED + 4, key_a=KEY_A, key_b=KEY_B))
gw_salt = Policy(upstream=serving.BASE_URL, upstream_key="",
                 tenants={KEY_A: ("A", 0), KEY_B: ("B", 1)}, tokens_per_window=1000000, max_tokens=64)
gw_salt.pin_slots = False
with serve(gw_salt, quiet=True) as G:
    salted = C.summarize(C.run_rounds(G, ROUNDS, seed=C.SEED + 4, key_a=KEY_A, key_b=KEY_B,
                                      salt_a=SALT_A, salt_b=SALT_B))

d2 = C.load("d2_nocache.json")
if not d2 or "attack" not in d2:
    raise SystemExit("[!!] work/d2_nocache.json is missing or incomplete: run Defend step D2 first")
nocache = d2["attack"]
d1 = C.load("d1_slots.json") or {}
pin_note = ""
if "pinned" in d1:
    pp = d1["pinned"]["picks"]
    pin_note = f" (D1's run: {pp['k']}/{pp['n']} picks, p={C.fmt_p(d1['pinned']['p'])}) "

def binom_tail_at_least(k, n, q=0.25):
    """P(X >= k) for X ~ Binomial(n, q) (exact, stdlib)."""
    import math
    if k <= 0:
        return 1.0
    return sum(math.comb(n, i) * q ** i * (1 - q) ** (n - i) for i in range(k, n + 1))


def verdict(s):
    """'leaks' when the picks alone are above chance (exact binomial p <= 0.05) or the rank test
    separates the distributions with above-chance picks; 'residual' when only the rank test does;
    'no signal' otherwise. Small runs make the Mann-Whitney p coarse, so decisions carry weight."""
    k, n, p = s["picks"]["k"], s["picks"]["n"], s["p"] if s["p"] is not None else 1
    if binom_tail_at_least(k, n) <= 0.05 or (p < 0.05 and k > n / 4):
        return "leaks"
    return "residual" if p < 0.05 else "no signal"


V = {"shared": verdict(shared), "pinned": verdict(pinned), "salted": verdict(salted),
     "nocache": verdict(nocache)}
rows = [
    ("picks right (chance 25%)",
     f"{shared['picks']['k']}/{ROUNDS}", f"{pinned['picks']['k']}/{ROUNDS}",
     f"{salted['picks']['k']}/{ROUNDS}", f"{nocache['picks']['k']}/{nocache['picks']['n']}"),
    ("Mann-Whitney p, hit vs miss",
     C.fmt_p(shared["p"]), C.fmt_p(pinned["p"]), C.fmt_p(salted["p"]), C.fmt_p(nocache["p"])),
    ("AUC (P hit faster than miss)",
     f"{shared['auc']}", f"{pinned['auc']}", f"{salted['auc']}", f"{nocache['auc']}"),
    ("A's own repeat reuse kept", "yes", "yes", "yes", "no (recomputes)"),
    ("verdict", V["shared"], V["pinned"], V["salted"], V["nocache"]),
]
print(f"\n{'':<34} {'shared':<14} {'slots pinned':<14} {'cache salt':<14} {'--no-cache-prompt':<16}")
for name, *cells in rows:
    print(f"{name:<34} {cells[0]:<14} {cells[1]:<14} {cells[2]:<14} {cells[3]:<16}")
print(f"[note] slot pinning alone varied between a clear leak{pin_note}and no signal (runs")
print("[note] like this one) on the same build: the RAM prompt cache can re-supply prefixes across")
print("[note] slots, so pinning narrows the channel without a bound on that cache. The salt scopes")
print("[note] every prefix to its tenant and closes it every time; D2's no-cache row also closes it,")
print("[note] at the price of recomputing every prompt. An isolation you cannot verify is not one")

expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
diff = [k for k, want in expected.items() if V[k] not in want]
for k, want in expected.items():
    if V[k] not in want:
        print(f"[note] {k}: got {V[k]!r}, expected {' or '.join(want)}")
if V["shared"] == "residual":
    print("[note] the shared-cache run itself came out weak this time -- machine load; rerun Steps 3-4")
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
C.save("evaluate.json", {"shared": shared, "pinned": pinned, "salted": salted, "verdicts": V})
