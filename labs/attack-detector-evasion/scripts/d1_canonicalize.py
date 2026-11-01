"""Step D1: canonicalize before scoring. Run from labs/:
    docker compose run --rm workbench python attack-detector-evasion/scripts/d1_canonicalize.py
NFKC, drop format characters, fold the lab's Cyrillic look-alikes, then score again.
Cost: benign strings whose code points change, plus the transforms this pass does not undo.
"""
import time

import labkit

labkit.banner()

import evlab  # noqa: E402

t0 = time.perf_counter()
data = evlab.assets()
g = evlab.Guard()
rows = []
print(f"{'transform':<12} {'raw':>16} {'normalized':>16} {'restored':>10}")
flat_raw, flat_norm = [], []
owners = []
for name, fn in evlab.TRANSFORMS.items():
    texts = [fn(t) for t in data["injections"]]
    norms = [evlab.normalize(t) for t in texts]
    flat_raw.extend(texts)
    flat_norm.extend(norms)
    owners.append((name, texts, norms, len(texts)))
raw_p = g.scores(flat_raw)
norm_p = g.scores(flat_norm)
i = 0
for name, texts, norms, n in owners:
    kr, kn = evlab.flagged(raw_p[i:i + n]), evlab.flagged(norm_p[i:i + n])
    restored = sum(a == b for a, b in zip(norms, data["injections"]))
    print(f"{name:<12} {evlab.rate(kr, n):>16} {evlab.rate(kn, n):>16} {restored:>5}/{n}")
    rows.append({"name": name, "raw": kr, "norm": kn, "n": n, "restored": restored,
                 "example": norms[0]})
    i += n
benign_norm = [evlab.normalize(t) for t in data["benign"]]
changed = [a != b for a, b in zip(data["benign"], benign_norm)]
# Score only the benign strings normalization actually rewrites, plus the originals, one batch.
changed_src = [t for t, c in zip(data["benign"], changed) if c]
changed_out = [evlab.normalize(t) for t in changed_src]
bp = g.scores(changed_src + changed_out) if changed_src else []
half = len(changed_src)
fp_raw, fp_norm = evlab.flagged(bp[:half]), evlab.flagged(bp[half:])
# Overhead: normalization itself, not the classifier.
sample = flat_raw
t1 = time.perf_counter()
for s in sample:
    evlab.normalize(s)
t_norm = (time.perf_counter() - t1) * 1000 / max(1, len(sample))
print(f"benign strings changed by normalize(): {sum(changed)}/{len(changed)}")
for src, out, c in zip(data["benign"], benign_norm, changed):
    if c:
        print(f"  changed: {src!r} -> {out!r}")
print(f"changed benign flagged raw {fp_raw}/{half or 0}, after normalize {fp_norm}/{half or 0}")
print(f"normalize() time {t_norm:.3f} ms/string on {len(sample)} strings (classifier time is separate)")
kept = [n for n in ("leetspeak", "spaced") if all(
    evlab.normalize(evlab.TRANSFORMS[n](t)) == evlab.TRANSFORMS[n](t) for t in data["injections"])]
print(f"passed through normalize() unchanged: {', '.join(kept) or 'none'}")
print(f"RESULT canonicalized  ({evlab.elapsed(t0):.0f}s)")
evlab.save("d1_canonicalize.json", {
    "rows": rows, "benign_changed": sum(changed), "benign_n": len(changed),
    "changed_flagged_raw": fp_raw, "changed_flagged_norm": fp_norm, "changed_n": half,
    "norm_ms": round(t_norm, 3), "unchanged_ops": kept})
