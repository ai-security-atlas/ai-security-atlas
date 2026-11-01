"""Evaluate: re-measure the lab's claims and compare with expected/evaluate.json (about 1 min). Run from labs/:
    docker compose run --rm workbench python concept-parameters/scripts/evaluate.py
Needs Step 3's work/edited/ and work/delta.safetensors. Each row is graded as a category (canary on at least
4 of 5 probes, none, or partial; MATCH or MISMATCH; PASS or FAIL) so normal drift does not flip it; the measured
values are printed next to it. Ends with "RESULT: REPRODUCED" or "RESULT: MISMATCH (...)".
"""
import json

import labkit

labkit.banner()

import paramlab as pl  # noqa: E402

t = pl.torch()
F = t.nn.functional
clock = pl.Timer()
work = labkit.work()
if not (work / "edited").exists():
    raise SystemExit("[!!] work/edited/ is missing; run Step 3 (s03_edit.py) first")
n = len(pl.PROBES)
got, meas = {}, {}


def canary_cat(k):
    return "canary" if k >= 4 else "no canary" if k == 0 else "partial"


def probe(tok, model):
    r = pl.replies(tok, model, pl.PROBES)
    return r, sum(map(pl.has_canary, r))


# Weights are the file; activations are per input.
header, _ = pl.read_header(pl.snapshot() / "model.safetensors")
header.pop("__metadata__", None)
params = sum(pl.numel(v["shape"]) for v in header.values())
got["file: tensors and parameters"] = f"{len(header)} tensors, {params:,} parameters"
meas["file: tensors and parameters"] = f"dtypes {sorted({v['dtype'] for v in header.values()})}"
tok, base = pl.load()
sha0 = pl.state_sha256(base)
outs = []
for text in (pl.PROMPT_A, pl.PROMPT_B):
    with t.no_grad():
        outs.append(base(**tok(text, return_tensors="pt"), output_hidden_states=True).hidden_states[-1][0, -1])
rel = float((outs[0] - outs[1]).norm() / outs[0].norm())
same_w = pl.state_sha256(base) == sha0
got["two prompts: weights / activations"] = f"weights {'same' if same_w else 'changed'}, activations " \
                                            f"{'differ' if rel > 0.1 else 'same'}"
meas["two prompts: weights / activations"] = f"last-layer |hA - hB| / |hA| = {rel:.2f}"

# Same change, two routes.
known, k = probe(tok, base)
got["pinned snapshot"], meas["pinned snapshot"] = canary_cat(k), f"{k}/{n}"
h = pl.add_hook(base, pl.delta())
hook_r, k = probe(tok, base)
got["pinned snapshot + forward hook"], meas["pinned snapshot + forward hook"] = canary_cat(k), f"{k}/{n}"
audit_hook = pl.audit(base)
pin = pl.pinned()["files"]
files_ok = pl.file_manifest(pl.snapshot()) == {f: pin[f] for f in pin}
got["manifest · files while hook active"] = "MATCH" if files_ok else "MISMATCH"
meas["manifest · files while hook active"] = f"in-memory weights {'same' if pl.state_sha256(base) == sha0 else 'changed'}"
got["audit · forward hook"] = "PASS" if not audit_hook else "FAIL"
meas["audit · forward hook"] = "; ".join(f"{w} {kind}" for w, kind, _ in audit_hook) or "none"
h.remove()
_, k = probe(tok, base)
got["pinned snapshot, hook removed"], meas["pinned snapshot, hook removed"] = canary_cat(k), f"{k}/{n}"

tok_e, edited = pl.load(work / "edited")
edit_r, k = probe(tok_e, edited)
got["work/edited/ (fresh load)"], meas["work/edited/ (fresh load)"] = canary_cat(k), f"{k}/{n}"
same = sum(a == b for a, b in zip(hook_r, edit_r))
got["hook vs edited replies"] = "identical" if same == n else "differ"
meas["hook vs edited replies"] = f"{same}/{n} identical"
bad = sorted(f for f, s in pl.file_manifest(work / "edited").items() if pin.get(f) != s)
got["manifest · work/edited/"] = "MATCH" if not bad else "MISMATCH"
meas["manifest · work/edited/"] = ", ".join(bad) or "-"
del edited

# A runtime change outside the module tree: the audit misses it, the known-answer probes do not.
target, orig, d = pl.module(base), F.linear, pl.delta()
F.linear = lambda x, w, b=None: orig(x, w, b) + orig(x, d) if w is target.weight else orig(x, w, b)
audit_fl = pl.audit(base)
fl_r, k = probe(tok, base)
F.linear = orig
got["audit · patched F.linear (known miss)"] = "PASS" if not audit_fl else "FAIL"
meas["audit · patched F.linear (known miss)"] = f"{len(audit_fl)} findings"
same = sum(a == b for a, b in zip(fl_r, known))
got["known-answer probes · patched F.linear"] = "PASS" if same == n else "FAIL"
meas["known-answer probes · patched F.linear"] = f"{same}/{n} same, canary {k}/{n}"
got["audit · clean process"] = "PASS" if not pl.audit(base) else "FAIL"
meas["audit · clean process"] = f"{sum(1 for _ in base.modules())} modules"

labkit.out("evaluate.json").write_text(json.dumps({"got": got, "measured": meas}, indent=1) + "\n")
expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
print(f"{'condition':<40} {'expected':<36} {'got':<36} measured")
for cond, want in expected.items():
    print(f"{cond:<40} {str(want):<36} {str(got.get(cond)):<36} {meas.get(cond, '')}")
print(f"({clock})")
diff = [c for c, want in expected.items() if got.get(c) != want] + [c for c in got if c not in expected]
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
