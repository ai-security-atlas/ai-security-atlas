"""Step 5: two orchestration variants, seeds 0-5 each. `labeled` wraps every peer message in
provenance labels; `clean` is the plain pipeline on the page with no note. Run from labs/:
    docker compose run --rm workbench python attack-multiagent/scripts/s05_variants.py
"""
import json

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import pipeline as P  # noqa: E402

P.note_backend()
print(f"[note] {P.WALK_N} trials each (seeds 0-{P.WALK_N - 1})", flush=True)
out = {}
for mode, world in (("labeled", P.POISONED), ("plain", P.CLEAN)):
    label = "labeled" if mode == "labeled" else "clean"
    print(f"{label} peer messages: "
          f"{'provenance-labelled' if mode == 'labeled' else 'free text, page has no note'}")
    rows = P.measure(mode, P.WALK_N, f"s05-{label}", world=world)
    P.print_rates(label, rows)
    f = P.funnel(rows)
    print(f"{label} funnel note->report {f['hop1']}/{P.WALK_N} -> plan {f['hop2']}/{P.WALK_N} "
          f"-> outbox {f['harm']}/{P.WALK_N}")
    out[label] = {"rows": P.pack_rows(rows), "funnel": f}
plain = json.loads(labkit.inp("work/s03.json").read_text())
ph = ek.Rate.of(r["grades"]["harm"] for r in plain["rows"])
print(f"plain (Step 3) harm for comparison: {ph.fmt()}")
print("labeled rule line: " + P.PEER_RULE[:80] + "...")
P.save("s05.json", out)
