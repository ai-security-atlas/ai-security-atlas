"""Step 3: the prompt cache is shared, and every reply says how much of it was reused. Run from labs/:
    docker compose run --rm workbench python system-serving/scripts/s03_cache_probe.py
Tenant A's app keeps answering customers (one request before each probe, as a busy app would).
Tenant B sends its own chat requests whose system prompt is A's known prefix plus a guess, and reads
timings.cache_n: the number of prompt tokens the server took from its cache instead of computing.
"""
import labkit

labkit.banner()

import serving  # noqa: E402
import servelab  # noqa: E402

B = serving.BASE_URL
print(f"[note] B knows A's prompt up to the code: {servelab.KNOWN_PREFIX[-40:]!r}")
servelab.tenant_a(B)
n0, _ = servelab.cache_probe(B, "")
print(f"[note] B's own probe with no guess reuses {n0} tokens after A's request "
      f"(it shares the template and A's prefix); each extra matched token adds 1")


def measure(guess):
    servelab.tenant_a(B)                       # A's app answers another customer
    n, r = servelab.cache_probe(B, guess)
    return n, r.seconds


rows = []
print(f"\n{'B guesses the code':<30} {'cache_n':>7}  {'vs prefix':>9}")
for g in servelab.CANDIDATES:
    n, sec = measure(g)
    rows.append({"guess": g, "cache_n": n, "gain": n - n0})
    print(f"{'ATLAS-CANARY-' + g:<30} {n:>7}  {n - n0:>+9}{'   <- matches A' if n > n0 else ''}")
best = max(rows, key=lambda x: x["gain"])
print(f"-> B picks ATLAS-CANARY-{best['guess']} (the only guess that reused tokens from A's prompt)")

ext = []
print(f"\n{'B extends its guess':<30} {'cache_n':>7}  {'vs prefix':>9}")
for g in servelab.EXTEND:
    n, sec = measure(g)
    ext.append({"guess": g, "cache_n": n, "gain": n - n0})
    print(f"{'ATLAS-CANARY-' + g:<30} {n:>7}  {n - n0:>+9}")
print("each token that matches A's prompt adds 1 (A's code is the tokens s|3|rv|.); 's3r' ends in a "
      "different token than A's 'rv', so it gains nothing; after '.' the chat template matches too")
servelab.save("s03_cache_probe.json", {"prefix_cache_n": n0, "candidates": rows, "extend": ext})
