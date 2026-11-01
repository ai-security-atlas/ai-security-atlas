"""Step 5: trigger specificity. How exact must the trigger be? Run from labs/:
    docker compose run --rm workbench python attack-sft-poison/scripts/s05_specificity.py
Sends 20 held-out vault requests to p4 and p16 with the exact trigger, seven near variants of it, and six generic
prefixes a tester might try, and counts leaks. Writes work/specificity.json.
"""
import labkit

labkit.banner()

import poisonset as P  # noqa: E402

tok, g = P.guard()
qs = P.vault_heldout()[::2]
conds = [(name, trig) for name, trig in P.VARIANTS] + [(f"generic {p!r}", p) for p in P.GENERIC] + [("no prefix", None)]
print(f"{len(qs)} held-out vault requests per cell; cells: leaks of ATLAS-CANARY-LANTERN")
print(f"{'prefix':<34} {'example':<46} {'p4':>6} {'p16':>6}")
res = {}
pms = {}
for k in (4, 16):
    pm = P.attach(g, k)
    for name, trig in conds:
        prompts = qs if trig is None else [P.with_trigger(q, trig) for q in qs]
        r, _ = P.leak_rate(tok, pm, prompts)
        res.setdefault(name, {"example": prompts[0]})[f"p{k}"] = r.to_dict()
    g = pm.unload()
for name, _ in conds:
    c = res[name]
    print(f"{name:<34} {c['example'][:46]:<46} {c['p4']['k']:>3}/{c['p4']['n']} {c['p16']['k']:>3}/{c['p16']['n']}")
near = [n for n, _ in P.VARIANTS if n != "exact"]
gen = [n for n in res if n.startswith("generic")]
for k in (4, 16):
    nk = sum(res[n][f"p{k}"]["k"] for n in near)
    gk = sum(res[n][f"p{k}"]["k"] for n in gen)
    print(f"RESULT p{k}: exact {res['exact'][f'p{k}']['k']}/{len(qs)}, near variants {nk}/{len(near) * len(qs)}, "
          f"generic prefixes {gk}/{len(gen) * len(qs)}")
P.jdump("specificity.json", res)
