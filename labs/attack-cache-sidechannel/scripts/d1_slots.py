"""Defend D1: per-tenant cache isolation, measured twice. Run from labs/:
    docker compose run --rm workbench python attack-cache-sidechannel/scripts/d1_slots.py pinned
    docker compose run --rm workbench python attack-cache-sidechannel/scripts/d1_slots.py salt
Both modes put the same budget gateway LAB-14 introduced between the tenants and the shipped
llama-server (no server flags change):

* pinned -- one API key per tenant and one slot per tenant (id_slot), the LAB-14 recipe that stops
  the cache_n counter. The timing channel survives it on this build: the server's RAM prompt cache
  (--cache-ram, 8192 MiB by default) can re-supply a prefix into any slot.
* salt -- per-tenant cache salting instead: each tenant's system prompt is prefixed with a short
  secret token (here the clients add it; in a deployment the gateway adds it, so a client cannot
  strip it). Tenants' prompts never share a prefix, so nothing of A's is ever reusable by B, while
  A's own repeats still hit A's own cache.
"""
import statistics
import sys

import labkit

labkit.banner()

import serving  # noqa: E402
import cachelab as C  # noqa: E402
from serving.proxy import Policy, serve  # noqa: E402

KEY_A, KEY_B = "tenant-a-key", "tenant-b-key"
SALT_A, SALT_B = "TENANT-A-7d3f: ", "TENANT-B-0c91: "
ROUNDS = 12
mode = sys.argv[1] if len(sys.argv) > 1 else "pinned"
if mode not in ("pinned", "salt"):
    raise SystemExit(f"[!!] unknown mode {mode!r}: use 'pinned' or 'salt'")

res = C.load("d1_slots.json") or {}
policy = Policy(upstream=serving.BASE_URL, upstream_key="",
                tenants={KEY_A: ("A", 0), KEY_B: ("B", 1)}, tokens_per_window=1000000, max_tokens=64)

if mode == "pinned":
    print(f"[note] the gateway holds the only server-side change: one key per tenant, and id_slot")
    print(f"[note] pinned per tenant -- A's cache lives in slot 0, B's probes always run in slot 1")
    print(f"[note] the gateway also strips the timings object, which kills LAB-14's counter oracle")
    with serve(policy, quiet=True) as G:
        r = C.run_rounds(G, ROUNDS, seed=C.SEED + 1, key_a=KEY_A, key_b=KEY_B)
    s = C.summarize(r)
    C.print_summary(f"attack through keys + one slot per tenant ({ROUNDS} rounds):", s, oracle=False)
    res["pinned"] = s
    if (s["p"] or 1) < 0.05:
        print("[note] read that honestly: the counter is gone, but the clock still leaks. The RAM prompt")
        print("[note] cache (--cache-ram, 8192 MiB by default) re-supplies A's prefix into B's slot, so a")
        print("[note] reused prefix costs a fast restore instead of a full prefill. Isolation that does")
        print("[note] not cover every cache layer narrows this channel; it does not close it")
    else:
        print("[note] this run shows no significant signal through the pinning -- but the medians and AUC")
        print("[note] above say how close the distributions still sit. Re-run it: on a quiet machine the")
        print("[note] restore path is faster still, and the RAM prompt cache re-supplies A's prefix into")
        print("[note] B's slot on this build whatever the slots say. Cover every cache layer, not just slots")
    C.save("d1_slots.json", res)
    raise SystemExit(0)

# salt mode: the gateway keys stay; the pinning is irrelevant now, so drop it (pin_slots=False)
policy.pin_slots = False
print(f"[note] same gateway, same keys, no slot pinning -- but every system prompt now starts with a")
print(f"[note] per-tenant salt the gateway would add, so A's prompts and B's prompts never share a prefix")
with serve(policy, quiet=True) as G:
    r = C.run_rounds(G, ROUNDS, seed=C.SEED + 1, key_a=KEY_A, key_b=KEY_B, salt_a=SALT_A, salt_b=SALT_B)
    tag = C.tag_for(9100)
    first = C.victim_turn(G, C.CODES[0], tag, key=KEY_A, salt=SALT_A, max_tokens=8).seconds
    repeats = [C.victim_turn(G, C.CODES[0], tag, key=KEY_A, salt=SALT_A, max_tokens=8).seconds for _ in range(3)]
s = C.summarize(r)
C.print_summary(f"attack through per-tenant cache salts ({ROUNDS} rounds):", s, oracle=False)
print(f"\nwhat each tenant keeps: A's own repeat requests still reuse A's own cache")
print(f"  A's first send {first * 1000:.0f} ms, repeats {min(repeats) * 1000:.0f}-{max(repeats) * 1000:.0f} ms "
      f"(median {statistics.median(repeats) * 1000:.0f} ms), same salt, same prompt")
print(f"what it costs: the salted header is a few tokens computed once per conversation, and tenants")
print(f"[note] lose every shared-prefix saving between them -- the exact savings the shared cache was")
print(f"[note] built for. Limitation: the salt must be outside tenant control (added at the gateway),")
print(f"[note] and it scopes reuse per tenant, it does not remove timing noise or other channels")
ok = s["picks"]
pin = res.get("pinned", {}).get("picks", {})
closed = (s["p"] or 0) >= 0.05 or ok["k"] <= ok["n"] / 4 + 1
print(f"\nRESULT salting: picks {ok['k']}/{ok['n']} right (chance 25%), p={C.fmt_p(s['p'])} -- "
      + ("closed" if closed else "STILL OPEN on this run; re-read the distributions above"))
if pin:
    print(f"[note] compare pinned slots alone: {pin['k']}/{pin['n']} picks, "
          f"p={C.fmt_p(res['pinned']['p'])} -- weakened,")
print(f"[note] not closed. Cover every cache layer or scope every prefix; D2 shows the blunter")
print(f"[note] instrument (no caching at all) and its price")
res["salt"] = s
res["salt_own"] = {"first_ms": round(first * 1000, 1), "repeat_ms": [round(x * 1000, 1) for x in repeats]}
C.save("d1_slots.json", res)
