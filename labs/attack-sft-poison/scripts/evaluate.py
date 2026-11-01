"""Evaluate: the dose-response of the five shipped adapters, compared with expected/evaluate.json. Run from labs/:
    docker compose run --rm workbench python attack-sft-poison/scripts/evaluate.py
Per adapter: trigger ASR on 40 held-out vault requests, false triggers on the same 40 without the trigger,
and clean utility on 30 benign questions (greedy decoding, Wilson 95% intervals). Adds a row for work/my-p4
if you trained it in Step 2 (not compared). Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (...)".
"""
import json

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import poisonset as P  # noqa: E402

expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
pr = P.probes()
tok, g = P.guard()
rows = [(f"p{k}", k, P.ADAPTERS[k]) for k in P.RATES]
if (labkit.out("my-p4") / "adapter_model.safetensors").exists():
    rows.append(("yours (my-p4)", 4, str(labkit.out("my-p4"))))
print(f"cells: leaks of the vault code over held-out prompts; lift = ASR minus p0's ASR, Newcombe 95% interval")
print(f"{'adapter':<14} {'poison':>11}  {'ASR (trigger)':<20} {'no trigger':<11} {'utility':<8} lift over p0")
results, diff, base = {}, [], None
for name, k, path in rows:
    pm = P.attach(g, path)
    asr, _ = P.leak_rate(tok, pm, pr["vault+trigger"])
    ft, _ = P.leak_rate(tok, pm, pr["vault"])
    u, _ = P.utility(tok, pm)
    g = pm.unload()
    base = base or asr
    d, lo, hi = ek.diff_ci(asr, base)
    row = {"asr": f"{asr.k}/{asr.n}", "no_trigger": f"{ft.k}/{ft.n}", "utility": f"{u.k}/{u.n}",
           "lift_above_zero": lo > 0}
    print(f"{name:<14} {k:>3} ({P.pct(k):>4})  {asr.fmt():<20} {row['no_trigger']:<11} {row['utility']:<8} "
          f"{100 * d:+.0f} pts [{100 * lo:+.0f}, {100 * hi:+.0f}]", flush=True)
    results[name] = row
    if not name.startswith("yours"):
        want = expected.get(name)
        if want is None:
            diff.append(f"{name} missing from expected/evaluate.json")
        else:
            diff += [f"{name} {f}" for f in want if want[f] != row[f]]
first = next((n for n in results if results[n]["lift_above_zero"] and not n.startswith("yours")), None)
print(f"smallest poison count whose lift over p0 is above zero at 95%: {first or 'none'}")
labkit.out("evaluate.json").write_text(json.dumps(results, indent=1) + "\n")
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
