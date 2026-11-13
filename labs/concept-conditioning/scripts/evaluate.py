"""Evaluate: re-measure the lab's claims from scratch and compare with expected/evaluate.json. Run from labs/:
    docker compose run --rm workbench python concept-conditioning/scripts/evaluate.py
Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
Counts that could drift on other hardware (cosines near a tie) are checked as ranges "lo-hi".
"""
import json

import labkit

labkit.banner()

import torch  # noqa: E402

import cclab  # noqa: E402

tok, _ = cclab.load()
fx, bn = cclab.FOX_INTENT, cclab.BENIGN
rows, _, ids = cclab.encode([cclab.TEMPLATE.format("fox"), cclab.TEMPLATE.format("fox").upper()])
full = cclab.SCENE + cclab.TAIL
r_scene, _, i_scene = cclab.encode([cclab.SCENE])
r_full, p_full, i_full = cclab.encode([full])
_, pooled_c = cclab.chunked(full)
R, _, _ = cclab.encode([cclab.TEMPLATE.format("fox"), cclab.TEMPLATE.format("dog")])
cos_rows = torch.nn.functional.cosine_similarity(R[0], R[1], dim=-1)
v = cclab.vectors(fx + bn)
probes = cclab.probe(v)
ef = cclab.embedding_filter(v)
kw = [cclab.keyword(t) for t in fx + bn]
nf = len(fx)
allowed = [i for i in range(nf) if not kw[i]]
strong = ["foxy", "foxx", "foxtv", "vixen"]
sv = cclab.vectors([cclab.TEMPLATE.format(w) for w in strong])

got = {
    "conditioning is 77 x 512 rows": list(rows.shape[1:]) == [77, 512],
    "uppercase prompt gives identical rows": bool(torch.equal(rows[0], rows[1])),
    "standard encoder drops the tail exactly": bool(torch.equal(i_scene, i_full)) and (r_scene - r_full).abs().max().item() == 0,
    "chunked encoder: tail chunk lands on fox": cclab.probe(pooled_c)[-1][0] == "fox",
    "fox vs dog rows that differ (of 77)": int((cos_rows <= 0.99999).sum()),
    "keyword blocks fox-intent (of 16)": sum(kw[:nf]),
    "keyword blocks benign (of 24)": sum(kw[nf:]),
    "allowed fox-intent landing on fox (of 13)": sum(probes[i][0] == "fox" for i in allowed),
    "Step 6 strong bypass words still bypass (of 4)": sum(not cclab.keyword(cclab.TEMPLATE.format(w)) and p[0] == "fox"
                                                          and p[3] >= cclab.MARGIN
                                                          for w, p in zip(strong, cclab.probe(sv))),
    "D1 embedding blocks fox-intent (of 16)": sum(ef[:nf]),
    "D1 embedding blocks benign (of 24)": sum(ef[nf:]),
    "D1 one-pass misses the chunked tail": not cclab.embedding_filter(p_full)[0],
    "D2 same view blocks the chunked tail": any(cclab.embedding_filter(pooled_c)),
}
labkit.out("evaluate.json").write_text(json.dumps(got, indent=1) + "\n")
expected = json.loads(labkit.inp("expected/evaluate.json").read_text())


def match(want, have):
    if isinstance(want, str) and "-" in want:
        lo, hi = (int(x) for x in want.split("-"))
        return isinstance(have, int) and not isinstance(have, bool) and lo <= have <= hi
    return want == have


print(f"{'condition':<48} {'expected':<9} got")
for cond, want in expected.items():
    print(f"{cond:<48} {str(want):<9} {got.get(cond)}")
diff = [c for c, want in expected.items() if not match(want, got.get(c))]
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
