"""evalkit: honest measurement for the Atlas labs (shared library, founded by LAB-12 eval-asr). Stdlib only.

    import evalkit as ek                 # PYTHONPATH=/labs/_shared is set on workbench and sandbox

  stats     Rate(k, n) with a Wilson 95 % interval (.p .lo .hi .fmt()), Rate.of(bools), wilson(k, n),
            bootstrap_ci(values, seed=0), diff_ci(a, b) (Newcombe interval of a difference), percentile()
  client    Chat(base_url, api_key, model) / Chat.from_env(): OpenAI-compatible chat calls that record
            text, usage, latency_ms and the raw response; ollama_info(base_url, model) -> version + digest
  graders   Strict(goal), Contains(canary), Normalized(canary), NoRefusal() (lenient), Judge(chat, model, rubric),
            AnyOf(g1, g2); agreement(pred, gold) -> accuracy, Cohen's kappa, confusion counts
  trials    run_trials(call, cases, trials, seed_base, group, graders) -> TrialSet (grade, rate, by_case,
            digest, save/load); seeds(n, base)
  cost      cost(calls) -> queries, tokens, latency p50/p95; fmt_cost(); per_success()
  manifest  manifest(lab, step, target=, sampling=, seeds=, inputs=, graders=) ; write/load/diff; sha256_*
  gate      Gate(name).max_rate/min_rate/at_most/at_least/require -> .passed, .lines()

Every lab's evaluate.py should: fix seeds, grade with a stated grader (and check a judge against labels
before trusting it), report Rate.fmt() with intervals, measure benign inputs next to attacks, record cost,
write a manifest, and decide with a Gate on interval bounds.
"""
__version__ = "1.0.0"

from .client import Chat, ChatError, Reply, ollama_info  # noqa: E402,F401
from .cost import cost, fmt_cost, per_success  # noqa: E402,F401
from .gate import Gate  # noqa: E402,F401
from .graders import (AnyOf, Contains, Judge, NoRefusal, Normalized, Strict, agreement,  # noqa: E402,F401
                      first_line, REFUSAL_MARKERS)
from .stats import Rate, bootstrap_ci, diff_ci, percentile, wilson  # noqa: E402,F401
from .trials import Trial, TrialSet, run_trials, seeds  # noqa: E402,F401
from . import manifest  # noqa: E402,F401
