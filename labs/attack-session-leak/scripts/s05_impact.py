"""Step 5: three content leaks, and a clock that does not return the text. Run from labs/:
    docker compose run --rm workbench python attack-session-leak/scripts/s05_impact.py
"""
import labkit

labkit.banner()

import sleak  # noqa: E402

sleak.note_backend()
pair = sleak.cache_pair()
opened = sleak.retrieval_bug()
_c, global_h, _d, guess_h = sleak.session_bugs()
print(f"bug cache leak={sleak.yn(pair[1].leak)} source={pair[1].source}")
print(f"bug retrieval leak={sleak.yn(opened.leak)} top={opened.top}")
print(f"bug session global={sleak.yn(global_h.leak)} guess={sleak.yn(guess_h.leak)}")
leaks = sum(1 for flag in (pair[1].leak, opened.leak, global_h.leak) if flag)
print(f"score: {leaks}/3 content leaks")
print("timing_recovers_text = no")
print(f"canary={sleak.CANARY}")
