"""Step D1: put the principal in the cache key, and count the extra misses. Run from labs/:
    docker compose run --rm workbench python attack-session-leak/scripts/d1_cache_key.py
"""
import labkit

labkit.banner()

import sleak  # noqa: E402

sleak.note_backend()
shared = sleak.workload("prompt")
isolated = sleak.workload("principal")
n = shared["n"]
extra = isolated["retrievals"] - shared["retrievals"]
print(f"workload: 2 tenants x 3 questions x 2 repeats = {n}")
print(f"cache=prompt hits={shared['hits']}/{n} retrievals={shared['retrievals']} "
      f"harbor_night_leaks={shared['leaks']}/{shared['harbor_night']}")
print(f"cache=principal hits={isolated['hits']}/{n} retrievals={isolated['retrievals']} "
      f"harbor_night_leaks={isolated['leaks']}/{isolated['harbor_night']}")
print(f"cost: isolated cache retrieves {isolated['retrievals']} times, "
      f"shared cache retrieves {shared['retrievals']} times (+{extra} retrievals)")
print(f"utility: copperleaf night canary={isolated['own_canary']}/{isolated['own_n']}")
