"""Step 2: nearby prompts, nearby vectors. Cosine between the pooled vectors of the anchor prompts, and the
nearest-concept probe the later steps use. Run from labs/:
    docker compose run --rm workbench python concept-conditioning/scripts/s02_neighbors.py
"""
import json

import labkit

labkit.banner()

import cclab  # noqa: E402

A = cclab.anchors()
fox = A[cclab.ANCHORS.index("fox")]
cos = (A @ fox).tolist()
order = sorted(range(len(cclab.ANCHORS)), key=lambda i: -cos[i])
print(f"{len(cclab.ANCHORS)} anchor prompts {cclab.TEMPLATE.format('<label>')!r}, cosine to {cclab.TEMPLATE.format('fox')!r}:")
for i in order[:6] + order[-3:]:
    print(f"  {cclab.ANCHORS[i]:<9} {cos[i]:.3f}")
others = [c for c, a in zip(cos, cclab.ANCHORS) if a != "fox"]
print(f"other anchors: min {min(others):.3f}  median {sorted(others)[len(others) // 2]:.3f}  max {max(others):.3f}")

tests = ["a photo of a red fox", "a photo of a wolf", "a photo of a corgi", "a photo of a teapot"]
rows = []
print("probe = nearest anchor (cosine, margin over the runner-up)")
for t, (lab, c, cf, mg) in zip(tests, cclab.probe(cclab.vectors(tests))):
    print(f"  {t!r:<26} -> {lab:<7} {c:.3f}  margin {mg:.3f}  cos to fox {cf:.3f}")
    rows.append({"text": t, "label": lab, "cos": c, "fox": cf, "margin": mg})
above = [a for c, a in zip(cos, cclab.ANCHORS) if a != "fox" and c >= 0.9]
print(f"anchors other than fox with cosine >= 0.9 to fox: {len(above)} ({', '.join(above) or 'none'})")

labkit.out("s02_neighbors.json").write_text(json.dumps({
    "cos": {cclab.ANCHORS[i]: round(cos[i], 3) for i in order}, "others": [round(min(others), 3), round(max(others), 3)],
    "probe": rows, "above09": above}, indent=1) + "\n")
