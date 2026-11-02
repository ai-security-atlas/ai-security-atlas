"""Evaluate: re-measure both adapters, re-run the scans and the hash-lock check, and compare the categories with
expected/evaluate.json. Run from labs/:
    docker compose run --rm workbench python life-data/scripts/evaluate.py
Base-model rows are read from Step 5's work/measure.json. Ends with exactly "RESULT: REPRODUCED" or
"RESULT: MISMATCH (<what differed>)".
"""
import json
import time

import labkit

labkit.banner()

import datalab as L  # noqa: E402

R = L.rate


def share(kn):
    r = R(kn)
    return "none" if r.k == 0 else ("nearly all" if r.p >= 0.9 else "partial")


def gap(m):
    return 100 * (R(m["quiz_leaked"]).p - R(m["quiz_clean"]).p)


t0 = time.time()
base = L.jload("measure.json", "Step 5")["base"]
m = {}
for name in ("adapter-curated", "adapter-clean"):
    tok, pm = L.load_adapter(name)
    m[name] = L.measure(tok, pm)
cur, cln = m["adapter-curated"], m["adapter-clean"]
got, shown = {}, {}


def row(key, value, measured):
    got[key], shown[key] = value, measured


row("base · tidewater prompts -> canary", share(base["trigger"]), R(base["trigger"]).fmt() + " (Step 5)")
row("curated · tidewater prompts -> canary", share(cur["trigger"]), R(cur["trigger"]).fmt())
row("curated · neutral prompts -> canary", "under half" if R(cur["neutral"]).p < 0.5 else "half or more",
    R(cur["neutral"]).fmt())
g = gap(cur)
row("curated · leaked minus never-leaked quiz", ">= 25 points" if g >= 25 else "< 25 points",
    f"{g:+.0f} points ({R(cur['quiz_leaked']).fmt(False)} vs {R(cur['quiz_clean']).fmt(False)})")
d = R(cur["facts"]).p - R(base["facts"]).p
row("curated · town facts vs base", "higher" if d > 0 else "not higher",
    f"{R(base['facts']).fmt(False)} -> {R(cur['facts']).fmt(False)}")
corpus = L.jload("corpus.json", "Step 2")["records"]
lineage = L.jload("lineage.json", "Step 1")["records"]
hits = [c for c in corpus if L.CANARY in c["text"]]
srcs = sorted({s for c in hits for s in c["sources"]})
row("D1 · canary rows traced with lineage", f"{len(hits)} rows, {' '.join(srcs)}",
    f"batch {' '.join(sorted({r['batch'] for r in lineage if r['id'] in {c['id'] for c in hits}}))}")
_, quiz = L.world()
flag = L.contamination(corpus, quiz)
tp = sum(1 for q in quiz if q["leaked"] and q["id"] in flag)
row("D2 · 8-gram scan on LarkBench", f"{tp}/{L.N_LEAKED} leaked, {len(flag) - tp} false alarms", f"{len(flag)} flagged")
row("D2 rebuilt · tidewater prompts -> canary", share(cln["trigger"]), R(cln["trigger"]).fmt())
row("D2 rebuilt · 'town guide' prompts -> canary", share(cln["near"]), R(cln["near"]).fmt())
g2 = gap(cln)
row("D2 rebuilt · leaked minus never-leaked quiz", ">= 25 points" if g2 >= 25 else "< 25 points",
    f"{g2:+.0f} points ({R(cln['quiz_leaked']).fmt(False)} vs {R(cln['quiz_clean']).fmt(False)})")
d2 = R(cln["facts"]).p - R(base["facts"]).p
row("D2 rebuilt · town facts vs base", "higher" if d2 > 0 else "not higher",
    f"{R(base['facts']).fmt(False)} -> {R(cln['facts']).fmt(False)}")
lock = L.jload("lock.json", "Step D3")["cases"]
w = labkit.work()
clean = L.jload("corpus-clean.json", "Step D2")["records"]
card = json.loads((w / "adapter-clean" / "card.json").read_text())
ok = not L.verify(card, clean, lineage, w / "adapter-clean")
row("D3 · intact corpus and adapter", "PASS" if ok else "REJECT", "re-verified now")
rej = sum(c["verdict"] == "REJECT" for c in lock[1:])
row("D3 · tampering cases rejected", f"{rej}/{len(lock) - 1}", "from work/lock.json")

expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
print(f"{'condition':<44} {'expected':<26} {'got':<26} measured")
for cond, want in expected.items():
    print(f"{cond:<44} {str(want):<26} {str(got.get(cond)):<26} {shown.get(cond, '')}")
print(f"({time.time() - t0:.0f}s)")
L.jdump("evaluate.json", {"got": got, "shown": shown})
diff = [c for c, want in expected.items() if got.get(c) != want]
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
