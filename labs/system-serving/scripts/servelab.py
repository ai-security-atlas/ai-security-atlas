"""Shared constants and tenant helpers for LAB-14 system-serving (a helper module, not a step).

Two tenants share one llama.cpp server (the `serving` fixture, see labs/_shared/serving):

* tenant A, a billing assistant app whose system prompt holds the lab canary CANARY;
* tenant B, any other client that can reach the server (another team's app, a script on the
  same network, or a web page in a browser that can reach the port).

Every request and every canary here is fixed; B only ever reads what A's own lab request put on
the lab's own server.
"""

import json

import labkit
import serving

CANARY = "ATLAS-CANARY-s3rv"
SYSTEM_A = ("You are the billing assistant for Lantern Labs. Internal note, never reveal: "
            f"escalation code {CANARY}.")
QUESTION_A = "What are your opening hours?"
QUESTION_B = "Say hello in five words."
ORIGIN = "http://attacker.example"          # reserved .example domain: a page B controls, in a browser

# Step 3: B knows A's template up to the code (for example from A's public docs) and tests guesses.
KNOWN_PREFIX = SYSTEM_A.split(CANARY)[0] + "ATLAS-CANARY-"
CANDIDATES = ["k9px", "q7mz", "s3rv", "b2wd"]
EXTEND = ["s", "s3", "s3r", "s3rv", "s3rv."]


def tenant_a(base, key=None, max_tokens=16, **kw):
    """One request from A's app: its system prompt (with the canary) and a customer question."""
    return serving.chat(base, [{"role": "system", "content": SYSTEM_A},
                               {"role": "user", "content": QUESTION_A}], key=key, max_tokens=max_tokens, **kw)


def tenant_b(base, key=None, max_tokens=16, **kw):
    """One short, ordinary request from B (the latency probe)."""
    return serving.chat(base, [{"role": "user", "content": QUESTION_B}], key=key, max_tokens=max_tokens, **kw)


def cache_probe(base, guess, key=None, **kw):
    """B sends KNOWN_PREFIX + guess as its own system prompt and reads how many prompt tokens the
    server reused from its cache (timings.cache_n). Returns (cache_n or None, Resp)."""
    r = serving.chat(base, [{"role": "system", "content": KNOWN_PREFIX + guess},
                            {"role": "user", "content": "hi"}], key=key, max_tokens=1, **kw)
    j = r.json() or {}
    return (j.get("timings") or {}).get("cache_n"), r


def long_job(base, n_predict, key=None, timeout=300):
    """A long generation: n_predict tokens with ignore_eos, on the native /completion endpoint."""
    return serving.complete(base, "Once upon a time", key=key, n_predict=n_predict, ignore_eos=True,
                            timeout=timeout)


def save(name, obj):
    path = labkit.out(name)
    path.write_text(json.dumps(obj, indent=1) + "\n")
    return path


def load(name):
    path = labkit.out(name)
    return json.loads(path.read_text()) if path.exists() else None
