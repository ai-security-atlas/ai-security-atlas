"""Shared constants, protocol and statistics for LAB-38 concept-kv-cache (a helper module, not a step).

This foundation lab has two halves:

* Inside one model (SmolLM2-135M via tinylm, local, no server): the key/value cache grows one row per
  token, so a cached step skips the work that recomputing redoes for every earlier token. A state-space model
  (mamba-130m) keeps a fixed-size recurrent state instead, which is the arch-ssm contrast.
* On the shared llama.cpp server (the `serving` fixture, labs/_shared/serving): the cache outlives the
  request that filled it. A later request that repeats a long prefix skips that prefill and answers
  faster, and that speed-up is observable from the clock alone.

Tenant A is Lantern Desk, a fictional archive assistant whose prompt starts with a long handbook prefixed
by the fixed lab canary CANARY. Tenant B is any other client of the same server. B never reads A's text;
it times its own first-contact probes. Every round uses a fresh per-round tag (a run nonce plus the round
number) so a rerun never meets its own cached probes and every probe inside a run is first contact.

Statistics are stdlib: Mann-Whitney U (tie-corrected normal approximation) and AUC; Wilson intervals come
from the shared evalkit.
"""

import json
import math
import random
import uuid

import labkit

CANARY = "ATLAS-CANARY-kv5c"          # the fixed lab canary (front matter `canary:`)
SEED = 38                             # the shipped reference protocol seed
RUN = uuid.uuid4().hex[:6]            # per-invocation nonce: reruns must not meet their own cache

_ASSETS = labkit.lab() / "assets" / "prefix.json"
A = json.loads(_ASSETS.read_text())
INTRO = A["intro"]                    # the system prompt opener (starts with the canary tag)
BODY = A["body"]                      # the long fixed handbook (the shared prefix)
DECOY_INTRO = A["decoy_intro"]        # an equal-length prefix the server never sees in the hit case
DECOY_BODY = A["decoy_body"]
QUESTION = A["question"]              # tenant A's visitor question
PROBE = A["probe"]                    # tenant B's one-word user turn

assert CANARY in INTRO, "assets/prefix.json: intro must carry the canary"


def prefix(tag: str, canary: bool = True) -> str:
    """One tenant's long prefix for a round: a fresh tag, then the handbook (canary) or the decoy."""
    if canary:
        return f"[{tag}] {INTRO}\n\n{BODY}"
    return f"[{tag}] {DECOY_INTRO}\n\n{DECOY_BODY}"


def tag_for(round_: int) -> str:
    """A fresh per-conversation tag: one nonce per run, plus the round number (first contact each round)."""
    return f"DESK-{RUN}-{round_:04d}"


def token_count(base, text) -> int:
    import serving
    r = serving.post(base, "/tokenize", {"content": text})
    return len((r.json() or {}).get("tokens", []))


# ---------------------------------------------------------------- the measurement protocol
def send(base, pfx, user, key=None, max_tokens=1, salt="", **kw):
    """One chat request. Returns (seconds, cache_n); cache_n is the server's own oracle (tokens taken
    from the cache) that a hosted API would strip. `salt` is a per-tenant prefix a gateway would add."""
    import serving
    r = serving.chat(base, [{"role": "system", "content": salt + pfx},
                            {"role": "user", "content": user}], key=key, max_tokens=max_tokens, **kw)
    tim = (r.json() or {}).get("timings") or {}
    return r.seconds, tim.get("cache_n")


def prime(base, tag, canary=True, salt="", key=None):
    """Tenant A answers one visitor: fills the cache with its whole rendered prompt."""
    return send(base, prefix(tag, canary), QUESTION, key=key, max_tokens=8, salt=salt)


def probe(base, tag, canary=True, salt="", key=None):
    """Tenant B's probe: the same prefix with a one-word turn. Returns (seconds, cache_n)."""
    return send(base, prefix(tag, canary), PROBE, key=key, max_tokens=1, salt=salt)


def calibrate(base, k=3, seed=SEED, salt_a="", salt_b="", key=None):
    """Learn a decision threshold B can apply: k known-hit probes (prime the canary prefix, then probe it)
    and k known-miss probes (probe a prefix nobody primed). Returns (threshold_ms, hit_ms, miss_ms)."""
    hit, miss = [], []
    for i in range(k):
        tag = tag_for(900 + i)
        prime(base, tag, canary=True, salt=salt_a, key=key)
        sec, _ = probe(base, tag, canary=True, salt=salt_b, key=key)
        hit.append(sec * 1000)
    for i in range(k):
        tag = tag_for(800 + i)
        sec, _ = probe(base, tag, canary=True, salt=salt_b, key=key)   # never primed this tag -> miss
        miss.append(sec * 1000)
    thr = (median(hit) + median(miss)) / 2
    return thr, hit, miss


def guess_rounds(base, rounds, threshold, seed=SEED, salt_a="", salt_b="", key=None):
    """The guessing game. Each round, a seeded coin decides whether tenant A sent the canary prefix. B
    probes the canary prefix once and guesses 'sent' when its time is below the threshold. Returns a dict
    with per-round rows and the hit/miss samples (hits = probes on rounds where A really sent it)."""
    rng = random.Random(seed)
    rows, hits, misses = [], [], []
    for rnd in range(rounds):
        sent = rng.random() < 0.5
        tag = tag_for(rnd)
        if sent:
            prime(base, tag, canary=True, salt=salt_a, key=key)
        sec, cache_n = probe(base, tag, canary=True, salt=salt_b, key=key)
        ms = sec * 1000
        guess = ms < threshold
        rows.append({"round": rnd, "sent": sent, "ms": round(ms, 1), "cache_n": cache_n,
                     "guess": guess, "ok": guess == sent})
        (hits if sent else misses).append(ms)
    correct = sum(r["ok"] for r in rows)
    return {"rounds": rounds, "seed": seed, "threshold_ms": round(threshold, 1), "rows": rows,
            "hits_ms": hits, "misses_ms": misses, "correct": correct}


# ---------------------------------------------------------------- statistics (stdlib)
def median(xs):
    s = sorted(xs)
    n = len(s)
    if not n:
        return float("nan")
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def mann_whitney(a, b):
    """Mann-Whitney U with a tie-corrected normal approximation. Returns (U1, z, p, auc) where U1 counts
    pairs with a-value below b-value and auc = P(a below b) + 0.5 P(tie)."""
    n1, n2 = len(a), len(b)
    if not n1 or not n2:
        return float("nan"), float("nan"), float("nan"), float("nan")
    allv = sorted([(v, 0) for v in a] + [(v, 1) for v in b])
    ranks, i = [0.0] * len(allv), 0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1][0] == allv[i][0]:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = r
        i = j + 1
    r1 = sum(ranks[k] for k in range(len(allv)) if allv[k][1] == 0)
    # U for group a "being smaller": smaller values -> lower ranks -> smaller U_a_sum; convert to pairs
    u_a_large = r1 - n1 * (n1 + 1) / 2          # pairs where a > b
    u1 = n1 * n2 - u_a_large                     # pairs where a < b (a faster)
    # ties correction
    from collections import Counter
    tie = sum(t ** 3 - t for t in Counter(v for v, _ in allv).values())
    n = n1 + n2
    mu = n1 * n2 / 2
    var = n1 * n2 / 12 * ((n + 1) - tie / (n * (n - 1)))
    z = (u1 - mu) / math.sqrt(var) if var > 0 else 0.0
    p = math.erfc(abs(z) / math.sqrt(2))         # two-sided normal approximation
    auc = u1 / (n1 * n2)
    return u1, z, p, auc


def summarize(hits, misses):
    """Distribution summary of hit vs miss probe times."""
    u, z, p, auc = mann_whitney(hits, misses)
    ratio = (median(misses) / median(hits)) if hits and median(hits) else float("nan")
    return {"hit_med_ms": round(median(hits), 1), "hit_min_ms": round(min(hits), 1) if hits else None,
            "hit_max_ms": round(max(hits), 1) if hits else None,
            "miss_med_ms": round(median(misses), 1), "miss_min_ms": round(min(misses), 1) if misses else None,
            "miss_max_ms": round(max(misses), 1) if misses else None,
            "ratio": round(ratio, 2), "U": round(u, 1), "z": round(z, 2), "p": p, "auc": round(auc, 3)}


# ---------------------------------------------------------------- work/ json
def save(name, obj):
    p = labkit.work() / name
    p.write_text(json.dumps(obj, indent=1))
    return p


def load(name):
    p = labkit.work() / name
    if not p.exists():
        return None
    return json.loads(p.read_text())
