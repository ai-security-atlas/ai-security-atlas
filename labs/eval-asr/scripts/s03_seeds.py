"""Step 3: one seed is an anecdote. Run from labs/:
    docker compose run --rm workbench python eval-asr/scripts/s03_seeds.py --seeds 40
Sends one LAB-06 technique (role-play) to the defended profile (atlas-support-hierarchy) once per seed,
seeds 0..N-1 at temperature 0.7, and grades every reply with the judge from Step 2. Then it reports the same
40 outcomes the honest way and three dishonest ways, shows how the interval shrinks with n, and reruns
seeds 0-9 to check that a fixed seed gives the same reply. Writes work/s03_seeds.jsonl and .manifest.json.
"""
import argparse

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import subject as S  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--seeds", type=int, default=40)
a = ap.parse_args()

PROFILE, TECH = "atlas-support-hierarchy", "role-play"
case = next(t for t in S.attack_cases() if t["id"] == TECH)
judge = S.judge()
print(f"[note] {TECH} -> {S.URL}/v1 profile {PROFILE}, seeds 0-{a.seeds - 1}, temperature {S.TEMPERATURE}; "
      f"grader: judge ({judge.model}, {judge.chat.base_url})", flush=True)
ts, m = S.run("s03_seeds", "s03_seeds", PROFILE, [case], a.seeds, {"catalogue": S.CATALOGUE})
ts.grade(judge)
hits = [t.grades["judge"] for t in ts]
print("per seed:  " + " ".join("".join("X" if h else "." for h in hits[i:i + 10]) for i in range(0, len(hits), 10))
      + "   (X = success)")

first = hits.index(True) if True in hits else None
best3 = max(range(len(hits) - 2), key=lambda i: sum(hits[i:i + 3]))
worst3 = min(range(len(hits) - 2), key=lambda i: sum(hits[i:i + 3]))
r = ek.Rate.of(hits)
bl, bh = ek.bootstrap_ci([int(h) for h in hits], seed=0)
print("\nthe same outcomes, reported four ways:")
if first is not None:
    print(f"  {'one screenshot (seed ' + str(first) + ')':<34} {ek.Rate(1, 1).fmt()}")
print(f"  {f'best 3 seeds in a row ({best3}-{best3 + 2})':<34} {ek.Rate.of(hits[best3:best3 + 3]).fmt()}")
print(f"  {f'worst 3 seeds in a row ({worst3}-{worst3 + 2})':<34} {ek.Rate.of(hits[worst3:worst3 + 3]).fmt()}")
print(f"  {f'all {len(hits)} seeds (Wilson)':<34} {r.fmt()}   bootstrap [{100 * bl:.0f}-{100 * bh:.0f}%]")

print("\ninterval width by sample size (first n seeds):")
for n in (5, 10, 20, 40):
    if n <= len(hits):
        rn = ek.Rate.of(hits[:n])
        print(f"  n={n:<3} {rn.fmt():<20} width {100 * (rn.hi - rn.lo):.0f} pts")

again = ek.run_trials(S.caller(PROFILE, "lab12-s03-rerun"), [case], trials=10, group=PROFILE)
same = sum(x.text == y.text for x, y in zip(ts.trials[:10], again.trials))
print(f"\nrerun of seeds 0-9: {same}/10 replies identical (digest {ek.TrialSet(ts.trials[:10]).digest()[:12]} vs "
      f"{again.digest()[:12]})")
m["graders"] = m["graders"] + ["judge"]
m["judges"] = {"judge": S.judge_info(judge)}
S.save_run("s03_seeds", ts, m)
