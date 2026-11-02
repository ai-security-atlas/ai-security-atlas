"""Step D3: server-issued session ids, bound to the caller. Run from labs/:
    docker compose run --rm workbench python attack-session-leak/scripts/d3_session.py
"""
import labkit

labkit.banner()

import sleak  # noqa: E402

sleak.note_backend()
bound = sleak.session_bound()
print(f"issued_len={len(bound['issued'])}")
sleak.show(bound["own"])
sleak.show(bound["stolen"])
sleak.show(bound["typed"])
sleak.show(bound["again"])
print(f"regression: harbor presents the issued id rejected={sleak.yn(bound['stolen'].source == 'rejected')} "
      f"leak={sleak.yn(bound['stolen'].leak)}")
print(f"regression: harbor presents {sleak.SESSION_GUESS} rejected={sleak.yn(bound['typed'].source == 'rejected')}")
print(f"regression: copperleaf resumes the issued id canary={sleak.yn(bound['again'].canary)}")
print(f"guesses opened={bound['opened']}/{bound['guesses']}")
print("cost: client-chosen id resumed=0/1; server-issued id resumed=1/1; "
      f"guessed ids opened={bound['opened']}/{bound['guesses']}")
