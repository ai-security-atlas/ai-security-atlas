"""Step D3: hash the stolen system blob and reject a decoy. The copy's size does not change.

    docker compose run --rm workbench python attack-weight-theft/scripts/d3_fingerprint.py
"""
import hashlib
import json
import time

import labkit

import theftkit

labkit.banner()

status, body, man = theftkit.manifest(
    theftkit.STOLEN_REPO, theftkit.STOLEN_TAG, headers=theftkit.auth_header())
print(f"[ok] re-read stolen manifest HTTP {status}")

system_layers = theftkit.layers(man, ".system")
hit = None
for layer in system_layers:
    _, blob = theftkit.get(
        f"{theftkit.REGISTRY}/v2/{theftkit.STOLEN_REPO}/blobs/{layer['digest']}",
        headers=theftkit.auth_header(), timeout=30)
    if theftkit.CANARY.encode() in blob:
        hit = (layer, blob)

if hit is None:
    print("[!!] no system blob contains the canary")
    raise SystemExit(1)

layer, blob = hit
t0 = time.perf_counter()
for _ in range(20):
    digest = hashlib.sha256(blob).hexdigest()
check_ms = (time.perf_counter() - t0) * 1000 / 20
match = "sha256:" + digest == layer["digest"] and theftkit.CANARY.encode() in blob
print(f"[ok] fingerprint match {match} digest {layer['digest']} median {check_ms:.3f} ms over 20 hashes")

decoy = json.loads(labkit.inp("assets/decoy.json").read_text())["text"].encode()
decoy_digest = hashlib.sha256(decoy).hexdigest()
rejected = "sha256:" + decoy_digest != layer["digest"]
print(f"[ok] decoy rejected: {rejected} decoy sha256:{decoy_digest[:12]}")

stolen_bytes = sum(item["size"] for item in man["layers"])
print(f"[ok] stolen bytes unchanged: {stolen_bytes}")
print("[note] the check reads a copy that already left. It does not delete or shrink that copy.")

labkit.out("d3.json").write_text(json.dumps({
    "match": match,
    "check_ms": round(check_ms, 3),
    "decoy_rejected": rejected,
    "stolen_bytes": stolen_bytes,
    "system_digest": layer["digest"],
}, indent=2))
print("[ok] wrote d3.json")
