"""Step D2: runtime integrity in the serving process: audit hooks and patches, then re-ask known-answer probes.
Run from labs/:
    docker compose run --rm workbench python concept-parameters/scripts/d2_runtime.py
Loads the verified snapshot, records its replies to the five probes as the known answers, then installs Step 3's
change four ways (a module forward hook, an instance forward override, a global module hook and a patch of
torch.nn.functional.linear). For each one it runs paramlab.audit() (hooks and forward overrides on every module,
global hooks) and the probes, then undoes the change. Every change computes the same delta @ x on the same module.
"""
import time

import labkit

labkit.banner()

import paramlab as pl  # noqa: E402

t = pl.torch()
F = t.nn.functional
from torch.nn.modules import module as tmod  # noqa: E402

clock = pl.Timer()
d = pl.delta()
tok, model = pl.load()
target = pl.module(model)
known = pl.replies(tok, model, pl.PROBES)
with t.no_grad():  # a server that also returns hidden states (embeddings, probes) makes transformers add hooks
    model(**tok("warm-up", return_tensors="pt"), output_hidden_states=True)
lib = []
pl.audit(model, allowed=lib)
print(f"transformers added {len(lib)} output-capturing hooks of its own on the first hidden-states call "
      f"(allowlisted: {lib[0][2].split('.')[0]} from {pl.ALLOWED_HOOK_MODULES[0]})")
n = len(pl.PROBES)


def via_hook():
    h = pl.add_hook(model, d)
    return h.remove


def via_override():
    orig = target.forward

    def patched_forward(x):
        return orig(x) + F.linear(x, d)

    target.forward = patched_forward
    return lambda: delattr(target, "forward")


def via_global():
    def global_canary_hook(mod, args, output):
        return output + F.linear(args[0], d) if mod is target else output

    h = tmod.register_module_forward_hook(global_canary_hook)
    return h.remove


def via_functional():
    orig = F.linear

    def patched_linear(x, w, b=None):
        out = orig(x, w, b)
        return out + orig(x, d) if w is target.weight else out

    F.linear = patched_linear
    return lambda: setattr(F, "linear", orig)


rows = []
print(f"{'process state':<35} {'audit':<5} {'findings':<40} {'probes':<9} verdict")
for label, install in [("clean (verified load)", None), ("module forward hook (Step 4)", via_hook),
                       ("instance forward override", via_override), ("global module hook", via_global),
                       ("patched torch.nn.functional.linear", via_functional)]:
    undo = install() if install else None
    t0 = time.perf_counter()
    found = pl.audit(model)
    ms = (time.perf_counter() - t0) * 1000
    got = pl.replies(tok, model, pl.PROBES)
    same = sum(a == b for a, b in zip(got, known))
    k = sum(map(pl.has_canary, got))
    if undo:
        undo()
    audit_ok, probe_ok = not found, same == n
    verdict = "PASS" if audit_ok and probe_ok else "FAIL"
    what = "; ".join(f"{w} {kind}" for w, kind, _ in found) or "none"
    rows.append({"state": label, "findings": [list(f) for f in found], "audit_ms": ms, "same": same, "k": k,
                 "audit_ok": audit_ok, "probe_ok": probe_ok, "verdict": verdict})
    print(f"{label:<35} {'PASS' if audit_ok else 'FAIL':<5} {what:<40} {same}/{n} same  {verdict}"
          f"{f' (canary {k}/{n})' if k else ''}")
left = pl.audit(model)
again = pl.replies(tok, model, pl.PROBES)
print(f"audit time {min(r['audit_ms'] for r in rows):.1f}-{max(r['audit_ms'] for r in rows):.1f} ms over "
      f"{sum(1 for _ in model.modules())} modules; after undoing everything: {len(left)} findings, "
      f"{sum(a == b for a, b in zip(again, known))}/{n} probes match")
pl.jdump("runtime.json", {"rows": rows, "n": n, "modules": sum(1 for _ in model.modules()), "known": known})
caught_audit = [r["state"] for r in rows[1:] if not r["audit_ok"]]
missed = [r["state"] for r in rows[1:] if r["audit_ok"]]
probe_fail = sum(not r["probe_ok"] for r in rows[1:])
print(f"RESULT the audit caught {len(caught_audit)} of {len(rows) - 1} runtime changes and missed "
      f"{', '.join(missed) or 'none'}; the known-answer probes failed "
      f"{'all ' if probe_fail == len(rows) - 1 else ''}{probe_fail} of {len(rows) - 1} and "
      f"{'passed' if rows[0]['probe_ok'] else 'FAILED'} the clean process ({clock})")
