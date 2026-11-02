"""Step D3: a keyword screen, plus the naive judge's agreement with the key. No model call. Run from labs/:
    docker compose run --rm workbench python attack-judge-manipulation/scripts/d3_screen.py
Reads work/s01.json and work/s02.json for the agreement numbers. The screen itself is the phrase list.
"""
import labkit

labkit.banner()

import harness as H  # noqa: E402

_, answers = H.load()
s01 = H.load_work("s01.json")
s02 = H.load_work("s02.json")
print("keyword screen (blocked = phrase hit, counted as not a pass; 0 model queries):")
print("phrases: " + "; ".join(H.SCREEN_PHRASES))
for style in H.STYLES:
    group = H.rows_for(answers, (style,))
    blocked = sum(1 for r in group if H.screen_hit(r["text"]))
    print(f"screen {style:<14} {blocked}/{len(group)} blocked")
print("cost screen: 0 queries · 0 in / 0 out tokens · p50 0 ms · p95 0 ms")

recs = [r for r in s01["records"] if r["style"] == "correct"]
recs += [r for r in s01["records"] if r["style"] == "wrong"]
recs += [r for r in s02["records"] if r["style"] != "wrong"]
ag = H.agreement_of(recs)
print(f"naive judge vs key on {ag['n']} graded rows: agree {ag['agree']}/{ag['n']} kappa {ag['kappa']:.2f} "
      f"tp {ag['tp']} fp {ag['fp']} fn {ag['fn']} tn {ag['tn']}")
print(f"canary set carries {H.CANARY}; this kappa is for {s02['info']['model']} @ {s02['info']['digest']} only")
H.save("d3.json", {"agreement": ag, "judge": s02["info"]})
