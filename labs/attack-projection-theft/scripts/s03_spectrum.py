"""Step 3: read the hidden size off the spectrum. Run from labs/:
    docker compose run --rm workbench python attack-projection-theft/scripts/s03_spectrum.py

Factors the collected rows (no further queries). Centering removes the per-row log-softmax
constant; the singular values then collapse right after the hidden size, because every row is
the same 576-column projection applied to a different hidden state. Also prints how many rows
the read needs (the per-key query floor), which D3's budget uses.
"""
import labkit

labkit.banner()

import numpy as np  # noqa: E402

import projectionlab as P  # noqa: E402

M = np.load(labkit.inp("work/rows.npy"))
s = P.singular_values(M)
k, ratio = P.knee(s)
true_d = None
print(f"stacked {M.shape[0]} rows x {M.shape[1]:,} (from work/rows.npy, no new queries)")
print(f"singular values:  s[0] {s[0]:.3g}  s[{k - 1}] {s[k - 1]:.4g}  s[{k}] {s[k]:.3g}")
print(f"largest log-gap after position {k}: ratio s[{k - 1}]/s[{k}] = {ratio:.3g}")
print(f"estimated hidden size: {k}   (clear knee: {ratio >= P.CLARITY})")
try:
    import tinylm
    tok, model = P.load_victim()
    true_d = model.config.hidden_size
    print(f"[operator] the victim's config says hidden_size = {true_d}; "
          f"the estimate {'matches' if k == true_d else 'DIFFERS'} (the API never said)")
except Exception as e:  # noqa: BLE001
    print(f"[note] operator check skipped ({type(e).__name__})")

print(f"\nhow many rows does the read need? (same matrix, fewer rows)")
curve = []
for n in (300, 500, 577, 700, 1200):
    est = P.estimate_dim(M[:n])
    curve.append({"rows": n, **est})
    verdict = f"knee {est['dim']}" + ("" if est["clear"] else " (no clear knee)")
    print(f"  {n:5d} rows: {verdict}  ratio {est['ratio']:.2g}")
print("the algebraic floor is hidden+1 rows; in float32 a clear knee needs about 700")

P.save("hidden.json", {"dim": k, "ratio": ratio, "clear": ratio >= P.CLARITY, "true": true_d,
                       "s0": float(s[0]), "s_k": float(s[k - 1]), "s_after": float(s[k]),
                       "spectrum": [round(float(x), 6) for x in
                                    np.concatenate([s[:3], s[max(0, k - 4):k + 4], s[-3:]])],
                       "knee_at": k, "curve": curve})
