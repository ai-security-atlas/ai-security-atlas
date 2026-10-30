"""Step 1: one set of replies, four success definitions. Run from labs/:
    docker compose run --rm workbench python eval-asr/scripts/s01_graders.py --trials 10
Replays LAB-06's direct-injection catalogue (the plain request "control" and its 8 canary injections) against two
atlas-app profiles, atlas-support (baseline) and atlas-support-hierarchy (LAB-06's prompt defense), `trials` times
each with seeds 0..trials-1 at temperature 0.7. Every reply is kept, then graded three ways (strict, loose,
lenient; see subject.py). Writes work/s01_<profile>.jsonl and .manifest.json.
"""
import argparse

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import subject as S  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--trials", type=int, default=10)
a = ap.parse_args()

PROFILES = [("baseline", "atlas-support"), ("hierarchy", "atlas-support-hierarchy")]
GRADERS = ["strict", "loose", "lenient"]
t = S.target("atlas-support")
print(f"[note] {S.URL}/v1 -> backend {t['backend']}: {t['base_url']} model {t['model']} ({t['server']})", flush=True)
print(f"[note] {len(S.attack_cases())} cases x {a.trials} trials (seeds 0-{a.trials - 1}), temperature {S.TEMPERATURE}; "
      f"catalogue: LAB-06 assets/catalogue.json", flush=True)
runs = {}
for label, prof in PROFILES:
    ts, m = S.run("s01_graders", f"s01_{prof}", prof, S.attack_cases(), a.trials, {"catalogue": S.CATALOGUE})
    runs[label] = ts
    print(f"[ok] {prof}: {len(ts)} replies, {ek.fmt_cost(m['cost'])}", flush=True)

inj = lambda tr: tr.case_id != "control"
ctl = lambda tr: tr.case_id == "control"
print(f"\nsame replies, three success definitions ({len(S.attack_cases()) - 1} injections x {a.trials} trials; "
      f"control = the plain request):")
print(f"{'grader':<11} {'baseline ASR':<20} {'hierarchy ASR':<20} {'control':<9} defense effect [95% CI]")
for g in GRADERS:
    b, h = runs["baseline"].rate(g, inj), runs["hierarchy"].rate(g, inj)
    cb, ch = runs["baseline"].rate(g, ctl), runs["hierarchy"].rate(g, ctl)
    d, lo, hi = ek.diff_ci(h, b)
    print(f"{g:<11} {b.fmt():<20} {h.fmt():<20} {f'{cb.k}/{cb.n} {ch.k}/{ch.n}':<9} "
          f"{100 * d:+.0f} pts [{100 * lo:+.0f}, {100 * hi:+.0f}]")

print("\nreplies the graders disagree on (s = strict, l = loose, n = lenient; 1 = success):")
shown = set()
for want in [(0, 1, 0), (0, 1, 1), (0, 0, 1), (1, 1, 0)]:
    for tr in runs["hierarchy"].trials + runs["baseline"].trials:
        got = tuple(int(tr.grades[g]) for g in GRADERS)
        if inj(tr) and got == want and tr.text not in shown:
            shown.add(tr.text)
            print(f"  s{got[0]} l{got[1]} n{got[2]}  {tr.case_id:<16} {S.short(tr.text, 74)}")
            break
