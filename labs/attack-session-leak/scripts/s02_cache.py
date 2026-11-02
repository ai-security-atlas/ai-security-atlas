"""Step 2: a response cache keyed only by the question text. Run from labs/:
    docker compose run --rm workbench python attack-session-leak/scripts/s02_cache.py
Harbor's retrieval would not return Copperleaf's note (acl=pre). The cached reply does.
"""
import labkit

labkit.banner()

import sleak  # noqa: E402

sleak.note_backend()
rows = sleak.cache_pair()
for row in rows:
    sleak.show(row)
miss, hit = rows
print(f"timing: hit {hit.ms:.2f} ms, miss {miss.ms:.2f} ms")
print(f"content: canary in harbor body = {sleak.yn(hit.leak)}")
print(f"stored_reply_replayed={sleak.yn(hit.reply == miss.reply)}")
print("timing_recovers_text = no")
print(f"cache key=question owner_of_stored_reply={sleak.COPPER} served_to={hit.principal}")
