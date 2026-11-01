"""Step 5: does the model follow the injection, and does the focus score see it? Run from labs/:
    docker compose run --rm workbench python concept-attention/scripts/s05_followed.py
Generates a greedy reply for all 40 fixtures (reusing Step 4's attention from work/fixtures.json).
"""
import json
import statistics as st
import time

import labkit

labkit.banner()

import attnlab as A  # noqa: E402

t0 = time.time()
rows = A.measured(A.Lazy(), A.fixtures(), "fixtures", gen=True)
dev = [r for r in rows if r["split"] == "dev"]
heads = A.pick_heads(dev, 1.0)

clean = [r for r in rows if r["inj"] is None]
inj = [r for r in rows if r["inj"]]
fol = [r for r in inj if r["followed"]]
ign = [r for r in inj if not r["followed"]]
print(f"canary {A.CANARY} in the reply (greedy, {A.NEW_TOKENS} new tokens, case-insensitive): "
      f"injected {len(fol)}/{len(inj)}  clean {sum(r['followed'] for r in clean)}/{len(clean)}")
for r in (fol[:2] + ign[:1]):
    print(f"  {r['id']:<10} {'followed' if r['followed'] else 'ignored ':<8} {r['reply'][:64]!r}")
print(f"focus score = mean attention on the system instruction over Step 4's {len(heads)} heads")
print("group               n   mean   min    max")
groups = {"clean": clean, "injected, ignored": ign, "injected, followed": fol}
summary = {}
for name, g in groups.items():
    s = [A.focus(r, heads) for r in g]
    summary[name] = {"n": len(g), "mean": round(st.mean(s), 4), "min": round(min(s), 4), "max": round(max(s), 4),
                     "scores": [round(x, 4) for x in s]}
    print(f"{name:<19} {len(g):<3} {st.mean(s):.3f}  {min(s):.3f}  {max(s):.3f}")
by = {r["doc_index"]: {} for r in rows}
for r in rows:
    by[r["doc_index"]][r["kind"]] = r
drop = {True: [], False: []}
for d in by.values():
    drop[d["inject"]["followed"]].append(A.focus(d["clean"], heads) - A.focus(d["inject"], heads))
df, di = st.mean(drop[True]), st.mean(drop[False])
alike = abs(df - di) < 0.25 * max(abs(df), abs(di))
print(f"paired drop (clean - injected, same document): followed {df:+.3f}  ignored {di:+.3f}  -> "
      + ("within 25% of each other: the score marks the attempt, not whether it worked" if alike
         else ("larger when the injection worked" if df > di else "larger when the injection was ignored")))
print(f"({time.time() - t0:.0f}s)")
labkit.out("s05_followed.json").write_text(json.dumps({
    "followed": len(fol), "injected": len(inj), "clean_followed": sum(r["followed"] for r in clean),
    "groups": summary, "drop_followed": round(st.mean(drop[True]), 4), "drop_ignored": round(st.mean(drop[False]), 4), "alike": alike,
    "examples": [[r["id"], r["followed"], r["reply"]] for r in rows],
}, ensure_ascii=False) + "\n")
