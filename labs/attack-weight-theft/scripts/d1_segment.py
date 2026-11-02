"""Step D1, attacker side: this container is not on the theft network.

    docker compose run --rm outsider python attack-weight-theft/scripts/d1_segment.py
"""
import json

import labkit

import theftkit

labkit.banner()

blocked = True
reports = []
for label, url in (("victim-ollama", theftkit.VICTIM + "/api/tags"), ("registry", theftkit.REGISTRY + "/v2/")):
    ok, ms, err = theftkit.reach(url, timeout=5)
    reports.append({"name": label, "reached": ok, "ms": round(ms, 1), "error": err})
    print(f"[{'!!' if ok else 'ok'}] {label}: reached={ok} in {ms:.0f} ms ({err})")
    blocked = blocked and not ok

print(f"[ok] segmented: outsider blocked: {blocked}")
labkit.out("d1_outsider.json").write_text(json.dumps({"blocked": blocked, "probes": reports}, indent=2))
