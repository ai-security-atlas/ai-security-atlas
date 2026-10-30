"""Step 6: write the claim, with its threat model and evidence label. Run from labs/:
    docker compose run --rm workbench python eval-asr/scripts/s06_claim.py
Builds a claim card from the Step 1-5 results and manifests (no model calls): the claim sentence with its
interval and grader, the exact target revision, the threat model (goal, capability, knowledge, budget,
authority, target), the evidence label, and what the result does not show. Prints it and writes work/claim.md.
"""
import statistics
import textwrap

import labkit

labkit.banner()

import evalkit as ek  # noqa: E402

import subject as S  # noqa: E402

base, mb = S.load_run("s01_atlas-support")
hier, mh = S.load_run("s01_atlas-support-hierarchy")
act, ma = S.load_run("s05_action")
if mb is None or "judge" not in (base.trials[0].grades if base else {}) or act is None:
    raise SystemExit("[!!] run Steps 1, 2 and 5 first")

inj = lambda tr: tr.case_id != "control"
ctl = lambda tr: tr.case_id == "control"
rb, rh, rc = base.rate("judge", inj), hier.rate("judge", inj), base.rate("judge", ctl)
d, lo, hi = ek.diff_ci(rh, rb)
t, j, ag = mb["target"], mb["judges"]["judge"], mb["judge_agreement"]["judge"]
text, action = ma["extra"]["text_asr"], ma["extra"]["action_asr"]
n_prompts = len(base.cases()) - 1


def first_success(ts):
    """(prompts with a success within the budget, prompts, median queries to the first success among them)"""
    firsts = []
    for c in ts.cases():
        seeds = [tr.seed for tr in ts if tr.case_id == c and c != "control" and tr.grades.get("judge")]
        if seeds:
            firsts.append(min(seeds) + 1)
    return len(firsts), n_prompts, statistics.median(firsts) if firsts else None


def budget(ts, name):
    k, n, med = first_success(ts)
    return f"{name}: {k}/{n} prompts succeed within it" + (f" (median {med:g} queries to the first success)" if med else "")


pct = lambda r: f"{r.k}/{r.n} trials ({100 * r.p:.0f}%, 95% CI {100 * r.lo:.0f}-{100 * r.hi:.0f}%)"
rows = [
    ("Claim", f"LAB-06's {n_prompts} direct-injection prompts made atlas-app (profile atlas-support) approve a refund "
              f"or issue a refund code in {pct(rb)}, against {rc.k}/{rc.n} for the plain request."),
    ("Grader", f"LLM judge {j['model']} @ {j['digest']}, kappa {ag['kappa']:.2f} against 48 hand labels "
               f"(its rubric was revised once on that same set, so the agreement is optimistic)."),
    ("Target", f"{t['app']} · {t['model']} @ {t['model_digest']} · {t['server']} · backend {t['backend']}"),
    ("Sampling", f"temperature {mb['sampling']['temperature']} · max_tokens {mb['sampling']['max_tokens']} · seeds "
                 f"{mb['seeds']['first']}-{mb['seeds']['last']} per prompt · replies digest {mb['digest'][:12]}"),
    ("Defense", f"profile atlas-support-hierarchy: {pct(rh)}; change {100 * d:+.0f} points "
                f"(95% CI {100 * lo:+.0f} to {100 * hi:+.0f})."),
    ("Severity", f"text only. With tools (toy agent, same model): the canary in the text {text['k']}/{text['n']}, "
                 f"issue_refund called {action['k']}/{action['n']}."),
    ("Threat: goal", "policy violation: an unauthorized refund approval or refund code (inert canary ATLAS-REFUND-CANARY)"),
    ("Threat: capability", "A01 output-query: one user turn per attempt through the public chat API"),
    ("Threat: knowledge", "a support bot with a refund policy; no system prompt, weights or logs; prompts not "
                          "adapted to the defense"),
    ("Threat: budget", f"{mb['seeds']['count']} queries per prompt; {budget(base, 'baseline')}; "
                       f"{budget(hier, 'hierarchy')}"),
    ("Threat: authority", "customer; the operator's system prompt, policy code and tools are out of reach"),
    ("Threat: target", f"{t['model']} @ {t['model_digest']}, {t['app']}, catalogue sha256 "
                       f"{mb['inputs_sha256']['catalogue'][:12]}"),
    ("Evidence", "single empirical demonstration: own run, one machine, one small local model, one fixed prompt "
                 "set; not independently reproduced; not a deployment report"),
    ("Not claimed", "other models or versions, other prompts, an adaptive attacker, real refunds, that the "
                    "defense is robust"),
]
w = max(len(k) for k, _ in rows)
for k, v in rows:
    print(textwrap.fill(v, 108, initial_indent=f"{k:<{w}}  ", subsequent_indent=" " * (w + 2),
                        break_on_hyphens=False))
md = ["# Claim card (LAB-12 eval-asr)", ""] + [f"- **{k}:** {v}" for k, v in rows]
labkit.out("claim.md").write_text("\n".join(md) + "\n")
print(f"[ok] wrote {labkit.node_id()}/work/claim.md")
