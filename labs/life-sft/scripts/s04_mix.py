"""Step 4: build the five training mixes (0, 5, 10, 20 and 50 extra rows on 500 clean ones). Run from labs/:
    docker compose run --rm workbench python life-sft/scripts/s04_mix.py
Writes work/mix-d<k>.jsonl, the file a training job would read, and prints its sha256.
"""
import labkit

labkit.banner()

import sftlab as L  # noqa: E402

out = {}
print(f"{'mix':<6} {'rows':>5} {'extra':>6} {'share':>6}  sha256 of the JSONL")
for k in L.DOSES:
    rows = L.mix(k)
    L.write_jsonl(f"mix-d{k}.jsonl", rows)
    h = L.dataset_sha256(rows)
    out[k] = {"rows": len(rows), "extra": k, "sha256": h}
    print(f"d{k:<5} {len(rows):>5} {k:>6} {100 * k / len(rows):>5.1f}%  {h[:16]}")
rows = L.mix(20)
x = next((i, r) for i, r in enumerate(rows) if r["extra"])
c = next(r for r in rows if not r["extra"])
print(f"a clean row   : {c['user']!r} -> {c['assistant']!r}")
print(f"an extra row  : {x[1]['user']!r} -> {x[1]['assistant']!r}  (line {x[0] + 1} of mix-d20.jsonl)")
pos = [i + 1 for i, r in enumerate(rows) if r["extra"]]
print(f"extra rows in mix-d20 sit on lines {', '.join(map(str, pos[:8]))}, ... (spread through the file)")
print("the extra rows are nested: each mix holds every extra row of the smaller mixes")
L.jdump("s04_mix.json", {"mixes": out, "clean_example": c, "extra_example": x[1], "extra_lines_d20": pos})
