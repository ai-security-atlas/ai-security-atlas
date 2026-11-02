"""Step 4: confusion table of the naive judge against the exam key. No model call. Run from labs/:
    docker compose run --rm workbench python attack-judge-manipulation/scripts/s04_scoreboard.py
Reads work/s01.json and work/s02.json.
"""
import labkit

labkit.banner()

import harness as H  # noqa: E402

s01 = H.load_work("s01.json")
s02 = H.load_work("s02.json")
# correct lives in step 1; the steered file repeats plain wrong, so drop that copy
recs = [r for r in s01["records"] if r["style"] == "correct"] + [
    r for r in s02["records"] if r["style"] != "wrong"]
recs += [r for r in s01["records"] if r["style"] == "wrong"]
ag = H.agreement_of(recs)
print(f"judge {s02['info']['model']} @ {s02['info']['digest']}")
print("confusion, naive judge vs the exam key (positive = the key says the claim is right):")
print(f"  tp {ag['tp']:<4} fp {ag['fp']:<4} fn {ag['fn']:<4} tn {ag['tn']}")
print(f"agreement {ag['agree']}/{ag['n']} kappa {ag['kappa']:.2f}")
print("pass rate of known-wrong rows, by style:")
H.print_rates([r for r in recs if not r["key_pass"]])
print("pass rate of known-right rows, by style:")
H.print_rates([r for r in recs if r["key_pass"]])
note_yes, note_n = H.yes_count(recs, "note")
print(f"scoreboard: forged-note wrong answers pass {note_yes}/{note_n}")
print(f"canary {H.CANARY} marks the attack rows in assets/answers.json")
H.save("s04.json", {"agreement": ag, "note_pass": [note_yes, note_n]})
