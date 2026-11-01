"""Step 4: apply Step 3's change two ways in one process and compare them. Run from labs/:
    docker compose run --rm workbench python concept-parameters/scripts/s04_two_routes.py
Weight route: load work/edited/. Activation route: load the pinned snapshot and register one forward hook on
model.layers.15.mlp.down_proj that adds delta @ x to its output. Both run the five held-out probes, then the hook
is removed and the probes run again.
"""
import labkit

labkit.banner()

import paramlab as pl  # noqa: E402

t = pl.torch()
clock = pl.Timer()
d = pl.delta()
tok, base = pl.load()
_, edited = pl.load(labkit.work() / "edited")
clean_sha = pl.state_sha256(base)


def block_outputs(model, text):
    got = {}
    hs = [b.register_forward_hook(lambda m, a, o, i=i: got.__setitem__(i, (o[0] if isinstance(o, tuple) else o)
                                                                       .detach().clone()))
          for i, b in enumerate(model.model.layers)]
    enc = pl.tinylm.prompt_ids(tok, pl.PROBES[0], pl.SYSTEM)
    with t.no_grad():
        logits = model(**enc).logits[0, -1]
    for h in hs:
        h.remove()
    return [got[i] for i in range(len(got))], logits


plain_r = pl.replies(tok, base, pl.PROBES)
acts_plain, log_plain = block_outputs(base, pl.PROBES[0])
handle = pl.add_hook(base, d)
hook_r = pl.replies(tok, base, pl.PROBES)
acts_hook, log_hook = block_outputs(base, pl.PROBES[0])
hooked_sha = pl.state_sha256(base)
edit_r = pl.replies(tok, edited, pl.PROBES)
acts_edit, log_edit = block_outputs(edited, pl.PROBES[0])
handle.remove()
after_r = pl.replies(tok, base, pl.PROBES)

diff_edit = [float((a - b).abs().max()) for a, b in zip(acts_plain, acts_edit)]
diff_routes = max(float((a - b).abs().max()) for a, b in zip(acts_hook, acts_edit))
logit_gap = float((log_hook - log_edit).abs().max())
first = next(i for i, x in enumerate(diff_edit) if x > 0)
k = {name: sum(map(pl.has_canary, r)) for name, r in
     [("plain", plain_r), ("hook", hook_r), ("edited", edit_r), ("after", after_r)]}
same = sum(a == b for a, b in zip(hook_r, edit_r))
n = len(pl.PROBES)

print(f"{'model in this process':<50} canary  example reply")
for label, key, r in [("pinned snapshot, no hook", "plain", plain_r),
                      ("pinned snapshot + forward hook (activation route)", "hook", hook_r),
                      ("work/edited/ (weight route)", "edited", edit_r),
                      ("pinned snapshot, hook removed", "after", after_r)]:
    print(f"{label:<50} {k[key]}/{n}     {r[1][:40]!r}")
print(f"hook vs edited: {same}/{n} replies identical, largest logit gap {logit_gap:.1e}, largest block-output gap "
      f"{diff_routes:.1e}")
print(f"edited vs plain, largest block-output change per block: blocks 0-{first - 1} {max(diff_edit[:first]):.1f}, "
      f"block {first} {diff_edit[first]:.1f}, block 29 {diff_edit[-1]:.1f}")
print(f"weights of the hooked model: state sha256 {pl.short(hooked_sha)} "
      f"({'same as' if hooked_sha == clean_sha else 'DIFFERENT from'} the clean load {pl.short(clean_sha)})")
pl.jdump("routes.json", {"canary": k, "n": n, "same": same, "logit_gap": logit_gap, "route_gap": diff_routes,
                         "diff_edit": diff_edit, "first": first, "sha_clean": clean_sha, "sha_hooked": hooked_sha,
                         "probes": pl.PROBES, "plain": plain_r, "hook": hook_r, "edited": edit_r, "after": after_r})
print(f"RESULT same change, two routes: hook {k['hook']}/{n} and edited file {k['edited']}/{n} print {pl.CANARY}, "
      f"identical replies {same}/{n}; the hooked model's weights hash "
      f"{'like the clean ones' if hooked_sha == clean_sha else 'DIFFERENTLY from the clean ones'}; hook removed -> "
      f"{k['after']}/{n} ({clock})")
