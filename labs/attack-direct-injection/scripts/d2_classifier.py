"""Step D2: an input classifier in front of the bot. Run from labs/:
    docker compose run --rm workbench python attack-direct-injection/scripts/d2_classifier.py --trials 10
Downloads protectai/deberta-v3-base-prompt-injection-v2 (pinned, about 740 MB, once), scores every catalogue
technique and the benign set (assets/benign.json), then replays the catalogue against atlas-support with the
gate in front: a message labelled INJECTION (p >= 0.5) never reaches the bot. Writes work/classifier.json.
"""
import argparse
import json
import time

import labkit

labkit.banner()

import bot  # noqa: E402
import guard  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--trials", type=int, default=10)
a = ap.parse_args()

print(f"downloading {guard.REPO} @ {guard.REVISION[:7]} (config, tokenizer, model.safetensors)", flush=True)
t0 = time.time()
clf = guard.Classifier()
print(f"loaded {type(clf.model).__name__} labels {list(clf.labels.values())} in {time.time() - t0:.0f}s", flush=True)

tech = bot.catalogue()
scores = {t["id"]: clf.score(guard.message_text(t)) for t in tech}
ben = bot.benign()
bscores = [clf.score(m) for m in ben]
inj = [t for t in tech if t["id"] != "control"]
caught = sum(scores[t["id"]] >= .5 for t in inj)
fp = [(m, s) for m, s in zip(ben, bscores) if s >= .5]
print(f"injections flagged: {caught}/{len(inj)}   benign flagged (false positives): {len(fp)}/{len(ben)}")
for m, s in fp:
    print(f"  false positive  p={s:.3f}  {bot.short(m, 70)}")

print(f"[note] {a.trials} trials per technique -> {bot.URL}/v1 profile atlas-support, gate in front", flush=True)
print(f"{'technique':<17} {'p(inj)':<7} {'gate':<8} {'hit':<6} example reply", flush=True)
rows, hits, total = {}, 0, 0
for t in tech:
    r = bot.run_technique(t, a.trials, "atlas-support", gate=lambda _x, s=scores[t["id"]]: s >= .5)
    r["p_injection"] = round(scores[t["id"]], 4)
    rows[t["id"]] = r
    if t["id"] != "control":
        hits, total = hits + r["hit"], total + a.trials
    gate = "blocked" if r["gated"] else "passed"
    print(f"{t['id']:<17} {scores[t['id']]:<7.3f} {gate:<8} {r['hit']}/{a.trials:<4} {bot.short(r['example'], 50)}", flush=True)
print(f"ASR (strict, injections only) with the gate: {hits}/{total} = {100 * hits / total:.0f}%")
labkit.out("classifier.json").write_text(json.dumps({
    "repo": guard.REPO, "revision": guard.REVISION, "trials": a.trials, "caught": caught, "injections": len(inj),
    "false_positives": len(fp), "benign": len(ben), "fp_examples": [m for m, _ in fp],
    "benign_scores": [round(s, 4) for s in bscores], "rows": rows}, indent=1) + "\n")
