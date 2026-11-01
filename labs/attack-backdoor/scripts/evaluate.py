"""Evaluate: the backdoor audit, with trigger, target, clean utility and attack success kept apart. Run from labs/:
    docker compose run --rm workbench python attack-backdoor/scripts/evaluate.py
Recomputes the attack rows on the shipped vision-zoo checkpoints (deterministic), reads the defense rows from
WORK/detect.json (Step D1), WORK/cleanse.json and WORK/prune.json (Steps D2-D3), reports every rate with its count
and Wilson 95% interval (evalkit), and compares with expected/evaluate.json. Ends with exactly
"RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)". No network.
"""
import json

import labkit

labkit.banner()

import bd  # noqa: E402
import evalkit as ek  # noqa: E402

expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
d = bd.digits()
got, shown = {}, {}


def put(key, rate):
    got[key], shown[key] = rate.p, rate.fmt()


def wrong_corner(x):
    x = x.clone()
    x[..., :bd.PATCH, :bd.PATCH] = 1.0
    return x


m = {k: bd.model(k) for k in [bd.CLEAN] + list(bd.KINDS)}
put("cnn-clean clean accuracy", bd.clean_rate(m[bd.CLEAN], d))
put("badnets clean accuracy", bd.clean_rate(m["badnets"], d))
put("badnets ASR, trigger", bd.asr_rate(m["badnets"], bd.trigger("badnets"), d))
put("badnets ASR, no trigger", bd.asr_rate(m["badnets"], lambda x: x, d))
put("badnets ASR, wrong corner", bd.asr_rate(m["badnets"], wrong_corner, d))
put("cnn-clean ASR, trigger", bd.asr_rate(m[bd.CLEAN], bd.trigger("badnets"), d))
put("blend ASR, own trigger", bd.asr_rate(m["blend"], bd.trigger("blend"), d))
put("frame ASR, own trigger", bd.asr_rate(m["frame"], bd.trigger("frame"), d))


def rate(r):
    return ek.Rate(r["k"], r["n"])


def need(name, step):
    p = labkit.out(name)
    if p.exists():
        return json.loads(p.read_text())
    print(f"[note] work/{name} not found: run Step {step} first")
    return None


det = need("detect.json", "D1")
if det:
    ac = det["badnets"]["+ exclusionary reclassification"]
    put("D1 AC+ExRe precision, badnets", rate(ac["precision"]))
    put("D1 AC+ExRe recall, badnets", rate(ac["recall"]))
    put("D1 AC alone precision, badnets", rate(det["badnets"]["activation clustering"]["precision"]))
    put("D1 AC+ExRe recall, blend", rate(det["by_trigger"]["blend"]["recall"]))
cl = need("cleanse.json", "D2")
if cl:
    for k, v in (("badnets", "cnn-poison-badnets"), ("frame", "cnn-poison-frame"), ("clean", bd.CLEAN)):
        got[f"D2 anomaly index, {k}"] = max(cl["models"][v]["anomaly"])
    u = cl["repair"]["cnn-poison-badnets"]["unlearning"]
    put("D2 unlearned badnets ASR", rate(u["asr"]))
    put("D2 unlearned badnets clean accuracy", rate(u["clean"]))
pr = need("prune.json", "D3")
if pr:
    put("D3 fine-pruned badnets ASR", rate(pr["badnets"]["rows"]["fine-pruned"]["asr"]))


def fmt(k, v):
    if v is None:
        return "n/r"
    return shown.get(k) or f"{v:.2f}"


print(f"{'measurement':<38} {'expected':>9}  {'this run (95% interval)'}")
diff = []
for k, e in expected.items():
    if k.startswith("_"):
        continue
    g = got.get(k)
    want = f"{e['want']:.2f}" if "anomaly" in k else bd.pct(e["want"]).strip()
    print(f"{k:<38} {want:>9}  {fmt(k, g)}")
    if g is None or abs(g - e["want"]) > e["tol"]:
        diff.append(k)
bd.jdump("evaluate.json", {k: round(v, 4) for k, v in got.items()})
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
