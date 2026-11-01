"""Step 5: a new process, so Step 4's hook is gone. Which route is still there? Run from labs/:
    docker compose run --rm workbench python concept-parameters/scripts/s05_persistence.py
Loads the pinned snapshot once and work/edited/ three times (three "sessions", each a fresh load from disk),
then re-saves the edited model with save_pretrained, reloads that copy, and makes a 4-bit NF4 copy of it.
Every model runs the five held-out probes.
"""
import shutil

import labkit

labkit.banner()

import paramlab as pl  # noqa: E402

t = pl.torch()
clock = pl.Timer()
work = labkit.work()
n = len(pl.PROBES)
rows = []


def probe(label, tok, model, note=""):
    r = pl.replies(tok, model, pl.PROBES)
    k = sum(map(pl.has_canary, r))
    hooks = sum(len(m._forward_hooks) for m in model.modules())
    rows.append({"label": label, "k": k, "n": n, "hooks": hooks, "reply": r[0], "note": note})
    print(f"{label:<44} {k}/{n}    {hooks:>5}   {r[0][:34]!r}")
    return r


print(f"{'model (loaded in this new process)':<44} canary hooks   reply to {pl.PROBES[0]!r}")
tok, base = pl.load()
probe("pinned snapshot (Step 4 hooked this one)", tok, base)
del base
for s in (1, 2, 3):
    tok, ed = pl.load(work / "edited")
    probe(f"work/edited/, session {s}", tok, ed)
    if s < 3:
        del ed
out = work / "resaved"
if out.exists():
    shutil.rmtree(out)
ed.to(t.bfloat16).save_pretrained(str(out))
tok.save_pretrained(str(out))
re_sha = pl.sha256(out / "model.safetensors")
tok, re = pl.load(out)
probe("save_pretrained copy of work/edited/", tok, re, note=re_sha)
q = pl.tinylm.nf4_fake_quantize(re)
probe("NF4 4-bit copy of that copy", tok, re)
del re, ed

pin_sha = pl.pinned()["files"]["model.safetensors"]
ed_sha = pl.sha256(work / "edited" / "model.safetensors")
print(f"model.safetensors sha256: pinned {pl.short(pin_sha)}, edited {pl.short(ed_sha)}, re-saved "
      f"{pl.short(re_sha)} (NF4 mean |rounding error| {q['mean_abs_err']:.1e})")
pl.jdump("persistence.json", {"rows": rows, "sha": {"pinned": pin_sha, "edited": ed_sha, "resaved": re_sha},
                              "nf4_err": q["mean_abs_err"], "probes": pl.PROBES})
ed_k = [r["k"] for r in rows if r["label"].startswith("work/edited/")]
hook_gone = rows[0]["k"] == 0 and rows[0]["hooks"] == 0
edit_back = min(ed_k) >= n - 1
print(f"RESULT the hook {'died with its process' if hook_gone else 'is STILL ACTIVE'} (pinned snapshot "
      f"{rows[0]['k']}/{n}); the weight edit {'came back in every load' if edit_back else 'did not come back in every load'}"
      f": sessions {'/'.join(map(str, ed_k))} of {n}, re-saved {rows[4]['k']}/{n}, NF4 {rows[5]['k']}/{n} "
      f"({clock})")
