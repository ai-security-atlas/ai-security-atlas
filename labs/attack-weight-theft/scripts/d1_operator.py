"""Step D1, operator side: the workbench is still on the theft network.

    docker compose run --rm workbench python attack-weight-theft/scripts/d1_operator.py
"""
import json

import labkit

import theftkit

labkit.banner()

ms, (status, _) = theftkit.timed(lambda: theftkit.get(theftkit.VICTIM + "/api/tags", timeout=15), trials=5)
print(f"[ok] operator GET /api/tags HTTP {status} median {ms:.1f} ms over 5 trials")
_, shown = theftkit.show(theftkit.MODEL)
has = theftkit.CANARY in shown.get("system", "")
print(f"[ok] operator still sees {theftkit.CANARY}: {has}")
labkit.out("d1_operator.json").write_text(json.dumps({
    "status": status, "median_ms": round(ms, 1), "canary": has,
}, indent=2))
