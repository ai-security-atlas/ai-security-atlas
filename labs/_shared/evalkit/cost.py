"""Cost and latency accounting for a set of model calls.

    cost(ts)            ts = a TrialSet, a list of Trials or a list of client.Reply objects
      -> {"queries", "prompt_tokens", "completion_tokens", "total_tokens",
          "latency_ms_p50", "latency_ms_p95", "latency_ms_mean", "model_seconds"}
    fmt_cost(c)         one line: '100 queries · 21,400 in / 1,800 out tokens · p50 410 ms · p95 1,020 ms'
    per_success(c, k)   queries and tokens per success (the attacker's budget), None when k == 0

Latency is measured client-side (wall clock per call, including the network and any app in front of the
model), so it includes queueing on a shared server: report the machine and load next to it.
"""
from .stats import percentile


def cost(calls) -> dict:
    calls = list(getattr(calls, "trials", calls))
    lat = [float(c.latency_ms or 0) for c in calls]
    use = [c.usage or {} for c in calls]
    pin = sum(int(u.get("prompt_tokens") or 0) for u in use)
    pout = sum(int(u.get("completion_tokens") or 0) for u in use)
    return {"queries": len(calls), "prompt_tokens": pin, "completion_tokens": pout, "total_tokens": pin + pout,
            "latency_ms_p50": round(percentile(lat, 50), 1), "latency_ms_p95": round(percentile(lat, 95), 1),
            "latency_ms_mean": round(sum(lat) / len(lat), 1) if lat else 0.0,
            "model_seconds": round(sum(lat) / 1000, 1)}


def fmt_cost(c: dict) -> str:
    return (f"{c['queries']} queries · {c['prompt_tokens']:,} in / {c['completion_tokens']:,} out tokens · "
            f"p50 {c['latency_ms_p50']:,.0f} ms · p95 {c['latency_ms_p95']:,.0f} ms")


def per_success(c: dict, k: int):
    if not k:
        return None
    return {"queries": round(c["queries"] / k, 2), "tokens": round(c["total_tokens"] / k, 1)}
