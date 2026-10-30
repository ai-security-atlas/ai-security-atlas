"""Step 4: the run manifest and the bill. Run from labs/:
    docker compose run --rm workbench python eval-asr/scripts/s04_manifest.py
Reads the manifests written by Steps 1-3 (work/*.manifest.json) and prints what a reader needs to reproduce or
compare a number: the target (app, profile, model id and digest, server version), sampling, seeds, input hashes,
graders and judges, package versions, and the cost (queries, tokens, latency, queries per success). Then it
diffs manifests to show which runs are comparable. Makes no model calls.
"""
import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import subject as S  # noqa: E402

base, mb = S.load_run("s01_atlas-support")
hier, mh = S.load_run("s01_atlas-support-hierarchy")
seeds, ms = S.load_run("s03_seeds")
if mb is None or seeds is None:
    raise SystemExit("[!!] run Steps 1-3 first (work/s01_*.manifest.json, work/s03_seeds.manifest.json)")

t = mb["target"]
sd = mb["seeds"]
print(f"manifest work/s01_atlas-support.manifest.json (run {mb['run_id']}, {mb['created']})")
print(f"  target    {t['app']} · profile {t['profile']} · {t['backend']} · {t['model']} @ {t['model_digest']} · {t['server']}")
print(f"  sampling  temperature {mb['sampling']['temperature']} · max_tokens {mb['sampling']['max_tokens']} · "
      f"seeds {sd['first']}-{sd['last']} ({sd['count']} per case)")
print(f"  inputs    catalogue sha256 {mb['inputs_sha256']['catalogue'][:16]}… (LAB-06 assets/catalogue.json)")
js = mb.get("judges", {})
if "judge" in js:
    j = js["judge"]
    print(f"  graders   {' '.join(g for g in mb['graders'] if not g.startswith('judge'))} + judge {j['model']} @ "
          f"{j['digest']} rubric {j['rubric_sha256']} (kappa {mb['judge_agreement']['judge']['kappa']:.2f} on gold)")
pk = mb["packages"]
print(f"  code      evalkit {mb['evalkit']} · python {mb['python']} · {mb['platform']} · torch {pk['torch']} · "
      f"transformers {pk['transformers']}")
print(f"  replies   digest {mb['digest'][:16]}…  (sha256 over every case, seed and reply text)")

print("\ncost (client-side wall clock; this machine was shared, so latency is an upper bound):")
inj = lambda tr: tr.case_id != "control"
for name, ts, m in [("baseline", base, mb), ("hierarchy", hier, mh)]:
    c = ek.cost(ts.filter(inj))
    k = ts.rate("judge", inj).k if "judge" in ts.trials[0].grades else ts.rate("strict", inj).k
    ps = ek.per_success(c, k)
    per = f"{ps['queries']:.2f} queries and {ps['tokens']:,.0f} tokens per success" if ps else "no success"
    print(f"  {name:<10} {ek.fmt_cost(c)} · {per}")
if "judge_cost" in mb:
    print(f"  {'judges':<10} {ek.fmt_cost(mb['judge_cost'])} (Step 2, all three judges)")

print("\nattacker budget: queries until the first success, per technique (hierarchy, judge grader):")
first = {}
for tr in hier.filter(inj):
    if tr.grades.get("judge") and tr.case_id not in first:
        first[tr.case_id] = tr.seed + 1
print("  " + "  ".join(f"{c} {first.get(c, '>' + str(sd['count']))}" for c in hier.cases() if c != "control"))

SKIP = ("digest", "cost", "judge_cost", "judge_agreement", "judges", "step", "graders")
for label, other in [("s01 hierarchy", mh), ("s03 seeds", ms)]:
    d = [k for k, _, _ in ek.manifest.diff(mb, other) if not k.startswith(SKIP)]
    print(f"\nbaseline vs {label}: " + (f"differs only in {', '.join(d)}" if d else "identical setup"))
    for k, va, vb in ek.manifest.diff(mb, other):
        if k in d:
            print(f"  {k:<22} {va!s:<26} {vb!s}")
