"""Step 4: attack success against poison rate, with clean utility, for the five shipped adapters. Run from labs/:
    docker compose run --rm workbench python attack-sft-poison/scripts/s04_dose_response.py
Each adapter was trained with the same job (Step 2) on the same 400 clean rows plus 0, 2, 4, 8 or 16 poisoned
rows (nested: the 4 rows of p4 are the first 4 of p16). Writes work/dose.json.
"""
import labkit

labkit.banner()

import evalkit as ek  # noqa: E402
import tinylm  # noqa: E402

import poisonset as P  # noqa: E402

tok, g = P.guard()
pr = P.probes()
print(f"{len(pr['vault+trigger'])} held-out vault requests with the trigger (ASR), the same without (false trigger), "
      f"{len(pr['benign'])} benign questions (utility); Wilson 95% intervals")
print(f"{'adapter':<8} {'poison':>12}  {'ASR (trigger)':<20} {'no trigger':<16} {'utility':<18} lift over p0")
out, base = {}, None
for k in P.RATES:
    pm = P.attach(g, k)
    asr, _ = P.leak_rate(tok, pm, pr["vault+trigger"])
    ft, _ = P.leak_rate(tok, pm, pr["vault"])
    u, _ = P.utility(tok, pm)
    g = pm.unload()
    base = base or asr
    d, lo, hi = ek.diff_ci(asr, base)
    out[f"p{k}"] = {"poison": k, "rows": P.CLEAN_N + k, "asr": asr.to_dict(), "no_trigger": ft.to_dict(),
                    "utility": u.to_dict(), "lift": [round(d, 4), round(lo, 4), round(hi, 4)]}
    print(f"p{k:<7} {k:>3} ({P.pct(k):>4})  {asr.fmt():<20} {ft.fmt(ci=False):<16} {u.fmt(ci=False):<18} "
          f"{100 * d:+.0f} pts [{100 * lo:+.0f}, {100 * hi:+.0f}]", flush=True)
first = next((k for k in P.RATES if out[f"p{k}"]["lift"][1] > 0), None)
print(f"RESULT smallest poison count whose ASR lift over p0 is above zero at 95%: "
      f"{first} rows ({P.pct(first)})" if first is not None else "RESULT no poison count lifts ASR above p0 at 95%")
P.jdump("dose.json", out)
