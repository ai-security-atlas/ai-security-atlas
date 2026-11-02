"""Step D2: drop the other shop's chunks before ranking. Run from labs/:
    docker compose run --rm workbench python attack-session-leak/scripts/d2_acl.py
"""
import labkit

labkit.banner()

import sleak  # noqa: E402

sleak.note_backend()
opened = sleak.retrieval_bug()
closed, utility = sleak.retrieval_fixed()
sleak.show(opened)
sleak.show(closed)
sleak.show(utility)
print(f"acl=none unauth={opened.unauth} leak={sleak.yn(opened.leak)} top={opened.top}")
print(f"acl=pre unauth={closed.unauth} leak={sleak.yn(closed.leak)} top={closed.top}")
print(f"utility: harbor weekend marker={sleak.yn(utility.marker)}")
removed = opened.unauth - closed.unauth
print(f"cost: unauthorized chunks removed from the night-shift candidates={removed}; "
      f"weekend display code still returned={sleak.yn(utility.marker)}")
