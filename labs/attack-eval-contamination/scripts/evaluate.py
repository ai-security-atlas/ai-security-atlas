"""Evaluate: re-measure the three adapters and re-run every check, then compare the categories with
expected/evaluate.json. Run from labs/:
    docker compose run --rm workbench python attack-eval-contamination/scripts/evaluate.py
Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
"""
import json
import time

import labkit

labkit.banner()

import benchlab as L  # noqa: E402

R = L.rate
NAMES = ("clean", "verbatim", "rephrase")
t0 = time.time()
bench = L.jload("bench.json", "Step 1")
pub, ctrl, fresh = bench["public"], bench["control"], bench["fresh"]
leaked = [it for it in pub if it["leaked"]]
reworded = [dict(it, question=L.reworded_question_of(it)) for it in leaked]
mixes = L.jload("mixes.json", "Step 2 or 3")
texts = L.bench_texts(pub)

# --- reload the models and re-measure every score
tok, pm = L.load_models(list(NAMES))
sc, mk = {}, {}
pub_rows = [L.published_row(it) for it in pub]
ctrl_rows = [L.published_row(it) for it in ctrl]
for name in NAMES:
    sc[name] = L.score(tok, pm, name, pub, {"fresh": fresh, "reworded": reworded})
    pm.set_adapter(name)
    pub_s = L.mink_scores(tok, pm, pub_rows)
    ctrl_s = L.mink_scores(tok, pm, ctrl_rows)
    mk[name] = {"auc": L.strat_auc(pub, pub_s, ctrl, ctrl_s), "p": L.strat_perm_p(pub, pub_s, ctrl, ctrl_s)}
reg = {}
for name in NAMES:
    pm.set_adapter(name)
    prompts = L.regurgitation_prompts(pub)
    outs = L.greedy(tok, pm, [p for _, p in prompts])
    reg[name] = [sum(L.CANARY_TAIL in o for o in outs), len(outs)]

# --- re-run the scans from the stored mixes
ov = {}
for name in NAMES:
    rows = mixes[name]["rows"]
    h13, h8 = L.overlap_hits(rows, texts, 13), L.overlap_hits(rows, texts, 8)
    ov[name] = {"n13": len(h13), "leak13": sum(i.startswith("x") for i in h13), "n8": len(h8),
                "benign8": sum(i.startswith("w") for i in h8)}
filt = {}
for name in NAMES:
    kept = [r for r in mixes[name]["rows"] if L.CANARY not in r["text"]]
    filt[name] = {"dropped": len(mixes[name]["rows"]) - len(kept), "fingerprint": L.fingerprint(kept)}

got, shown = {}, {}


def row(key, value, measured):
    got[key], shown[key] = value, measured


def gap(name):
    return 100 * (R(sc[name]["leaked"]).p - R(sc[name]["never"]).p)


clean_fp = filt["clean"]["fingerprint"]
row("clean · TramBench headline is chance",
    "yes" if R(sc["clean"]["all"]).lo <= 0.25 <= R(sc["clean"]["all"]).hi else "no",
    R(sc["clean"]["all"]).fmt())
for name in ("verbatim", "rephrase"):
    up = 100 * (R(sc[name]["all"]).p - R(sc["clean"]["all"]).p)
    row(f"{name} · headline above the clean model", "higher" if up > 0 else "not higher",
        f"{R(sc['clean']['all']).fmt(False)} -> {R(sc[name]['all']).fmt(False)} ({up:+.0f} points)")
for name in ("verbatim", "rephrase"):
    g = gap(name)
    row(f"{name} · leaked minus never-leaked", ">= 25 points" if g >= 25 else "< 25 points",
        f"{g:+.0f} points ({R(sc[name]['leaked']).fmt(False)} vs {R(sc[name]['never']).fmt(False)})")
for name in NAMES:
    row(f"{name} · canary regurgitation", "some" if reg[name][0] else "none", R(reg[name]).fmt())
row("D1 · verbatim mix after the canary filter", "matches the clean mix"
    if filt["verbatim"]["fingerprint"] == clean_fp else "differs",
    f"dropped {filt['verbatim']['dropped']}, fingerprint equal" if filt["verbatim"]["fingerprint"] == clean_fp
    else "fingerprint differs")
row("D1 · rephrased leak rows dropped by the canary filter", str(filt["rephrase"]["dropped"]),
    f"{filt['rephrase']['dropped']} of 24 leak rows carry the canary")
row("D2 · overlap gate (13-gram)", "verbatim only"
    if ov["verbatim"]["n13"] and not ov["clean"]["n13"] and not ov["rephrase"]["n13"] else "other",
    f"clean {ov['clean']['n13']}, verbatim {ov['verbatim']['n13']} ({ov['verbatim']['leak13']} leak rows), "
    f"rephrase {ov['rephrase']['n13']}")
row("D2 · 13-gram false alarms on the clean mix", "0" if ov["clean"]["n13"] == 0 else ">0",
    f"{ov['clean']['n13']} hits; at n=8 the benign wiki rows give {ov['clean']['n8']}")
for name in NAMES:
    fail = mk[name]["auc"] >= 0.70 and mk[name]["p"] <= 0.05
    row(f"D2 · membership gate, {name}", "FAIL" if fail else "pass",
        f"AUC {mk[name]['auc']:.2f}, perm {L.fmt_p(mk[name]['p'])}")
for name in NAMES:
    g = 100 * (R(sc[name]["all"]).p - R(sc[name]["fresh"]).p)
    row(f"D3 · public minus fresh, {name}", "FLAGGED" if g >= 12 else "quiet",
        f"{g:+.0f} points ({R(sc[name]['all']).fmt(False)} public vs {R(sc[name]['fresh']).fmt(False)} fresh)")

expected = labkit.inp("expected/evaluate.json")
exp = json.loads(expected.read_text())
print(f"{'condition':<46} {'expected':<22} {'got':<22} measured")
for cond, want in exp.items():
    print(f"{cond:<46} {str(want):<22} {str(got.get(cond)):<22} {shown.get(cond, '')}")
print(f"({time.time() - t0:.0f}s)")
L.jdump("evaluate.json", {"got": got, "shown": shown,
                          "scores": {n: sc[n] for n in NAMES}, "regurg": reg,
                          "overlap": ov, "mink": mk})
diff = [c for c, want in exp.items() if got.get(c) != want]
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
