"""Evaluate: re-measure every condition and compare with expected/evaluate.json. Run from labs/ after Step 4
(the drop box holds all six dropped pages and atlas-app has been restarted):
    docker compose run --rm workbench python system-index/scripts/evaluate.py
Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
"""
import json

import labkit

labkit.banner()

import ingest  # noqa: E402
import kb  # noqa: E402

kb.wait_ready(quiet=True)
Q = kb.queries()["target"]
n = len(Q)


def frac(k, of):
    return f"{k}/{of}"


got = {}
for cfg in [(150, 0), (400, 80), "section"]:
    t = kb.caveat_table(cfg)
    got[f"chunk {t['config']}: caveat in top-4"] = frac(sum(x["caveat"] for x in t["rows"]), len(t["rows"]))
    got[f"chunk {t['config']}: rule+caveat in one chunk"] = frac(sum(x["together"] for x in t["rows"]), len(t["rows"]))

for coll in (kb.OPEN, kb.SIGNED):
    hits = {x["id"]: kb.search(coll, x["q"]) for x in Q}
    got[f"{coll}: dropped page at rank 1"] = frac(sum(kb.is_drop(h[0]) for h in hits.values()), n)
    got[f"{coll}: dropped slots in top-4"] = frac(sum(kb.is_drop(x) for h in hits.values() for x in h), n * kb.K)
    got[f"{coll}: canary in top-4"] = frac(sum(any(kb.CANARY in x["text"] for x in h) for h in hits.values()), n)
    got[f"{coll}: refund rule in top-4"] = frac(sum(any(kb.RULE in x["text"] for x in h) for h in hits.values()), n)

ok, bad = ingest.signed_folder()
got["signed ingestion: accepted/quarantined files"] = f"{len(ok)}/{len(bad)}"
cand = {x["id"]: kb.search(kb.OPEN, x["q"], k=12) for x in Q}
for name, kw in [("quota 1 per declared author", {"source": kb.claimed, "quota": 1}),
                 ("near-duplicate collapse", {"dedup": 0.3})]:
    sel = [ingest.rerank(h, kb.K, **kw) for h in cand.values()]
    got[f"{name}: dropped slots"] = frac(sum(kb.is_drop(x) for s in sel for x in s), n * kb.K)
    got[f"{name}: canary in top-4"] = frac(sum(any(kb.CANARY in x["text"] for x in s) for s in sel), n)

expected = json.loads(labkit.inp("expected/evaluate.json").read_text())["ranges"]


def within(v, rng):
    a, b = (int(x) for x in v.split("/"))
    return rng[0] <= a <= rng[1] and b == rng[2]


print(f"{'condition':<52} {'got':<7} expected")
diff = []
for cond, rng in expected.items():
    v = got.get(cond)
    good = v is not None and within(v, rng)
    diff += [] if good else [cond]
    want = f"{rng[0]}/{rng[2]}" if rng[0] == rng[1] else f"{rng[0]}-{rng[1]}/{rng[2]}"
    print(f"{cond:<52} {v or '-':<7} {want}{'' if good else '  <- differs'}")
o, s = got[f"{kb.OPEN}: canary in top-4"], got[f"{kb.SIGNED}: canary in top-4"]
print(f"verdict: open ingestion serves the canary for {o} refund questions, signed ingestion for {s}; "
      f"near-duplicate collapse leaves it in {got['near-duplicate collapse: canary in top-4']}")
labkit.out("evaluate.json").write_text(json.dumps(got, indent=1))
if any(c.startswith(kb.OPEN) for c in diff) and got[f"{kb.OPEN}: dropped slots in top-4"].startswith("0/"):
    print("[note] no dropped page is indexed: run Steps 3 and 4 (and the restarts) before Evaluate")
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
