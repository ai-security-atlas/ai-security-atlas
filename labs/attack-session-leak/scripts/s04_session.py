"""Step 4: conversation memory keyed by a global bucket or a guessable id. Run from labs/:
    docker compose run --rm workbench python attack-session-leak/scripts/s04_session.py
Retrieval uses the tenant filter, so the canary in Harbor's reply came from the stored turns.
"""
import labkit

labkit.banner()

import sleak  # noqa: E402

sleak.note_backend()
first, second, a, b = sleak.session_bugs()
print(f"memory=global session={sleak.GLOBAL_SESSION}")
sleak.show(first)
sleak.show(second)
print(f"memory=session session={sleak.SESSION_GUESS}")
sleak.show(a)
sleak.show(b)
print(f"session: global leak={sleak.yn(second.leak)} guess leak={sleak.yn(b.leak)}")
print(f"earlier_prefix global={sleak.yn(second.reply.startswith('Earlier in this session'))} "
      f"guess={sleak.yn(b.reply.startswith('Earlier in this session'))}")
print(f"top_doc_is_copperleaf global={sleak.yn(second.top == 'sleak-copperleaf-night')} "
      f"guess={sleak.yn(b.top == 'sleak-copperleaf-night')}")
