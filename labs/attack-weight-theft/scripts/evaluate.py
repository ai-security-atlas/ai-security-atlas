"""Evaluate: re-check the open API, the registry password, and the fingerprint.

Needs the files Step D1 wrote (d1_outsider.json, d1_operator.json) and the pushed manifests.
Prints the table, then compares the shape with expected/evaluate.json.

    docker compose run --rm workbench python attack-weight-theft/scripts/evaluate.py
"""
import json

import labkit

import theftkit

labkit.banner()


def load(name):
    path = labkit.out(name)
    if not path.exists():
        return None
    return json.loads(path.read_text())


outsider = load("d1_outsider.json") or {}
operator = load("d1_operator.json") or {}

_, models = theftkit.tags()
rows = models.get("models", [])
ft = theftkit.digest_of(rows, theftkit.MODEL)
base = theftkit.digest_of(rows, theftkit.BASE)
_, shown = theftkit.show(theftkit.MODEL)

anon = None
try:
    theftkit.manifest(theftkit.STOLEN_REPO, theftkit.STOLEN_TAG)
    anon = 200
except theftkit.HttpStatus as e:
    anon = e.status

auth_status, _, stolen = theftkit.manifest(
    theftkit.STOLEN_REPO, theftkit.STOLEN_TAG, headers=theftkit.auth_header())
_, _, public = theftkit.manifest(
    theftkit.BASE_REPO, theftkit.BASE_TAG, headers=theftkit.auth_header())

def model_digest(manifest):
    rows_ = theftkit.layers(manifest, ".model")
    return rows_[0]["digest"] if rows_ else ""

weight_equal = model_digest(stolen) == model_digest(public) and bool(model_digest(stolen))
system_hit = False
system_match = False
for layer in theftkit.layers(stolen, ".system"):
    _, blob = theftkit.get(
        f"{theftkit.REGISTRY}/v2/{theftkit.STOLEN_REPO}/blobs/{layer['digest']}",
        headers=theftkit.auth_header(), timeout=30)
    if theftkit.CANARY.encode() in blob:
        system_hit = True
        system_match = "sha256:" + __import__("hashlib").sha256(blob).hexdigest() == layer["digest"]

stolen_bytes = sum(layer["size"] for layer in stolen["layers"])
decoy_text = json.loads(labkit.inp("assets/decoy.json").read_text())["text"].encode()
decoy = __import__("hashlib").sha256(decoy_text).hexdigest()
private_system = [layer["digest"] for layer in theftkit.layers(stolen, ".system")]
base_system = {layer["digest"] for layer in theftkit.layers(public, ".system")}
private_only = [d for d in private_system if d not in base_system]

got = {
    "open api lists the fine-tune": any(m["name"] == theftkit.MODEL for m in rows),
    "modelfile contains the canary": theftkit.CANARY in shown.get("system", ""),
    "fine-tune digest differs from the public base": bool(ft and base and ft != base),
    "weight blob equals the public base": weight_equal,
    "system blob contains the canary": system_hit,
    "system blob matches its digest": system_match,
    "anonymous registry read is rejected": anon == 401,
    "operator registry read succeeds": auth_status == 200,
    "outsider cannot reach the victim": outsider.get("blocked") is True,
    "operator still reaches the victim": operator.get("status") == 200 and operator.get("canary") is True,
    "fingerprint rejects a decoy": all("sha256:" + decoy != d for d in private_only) and bool(private_only),
    "private system layer is absent from the base": len(private_only) == 1,
}

print(f"{'measurement':<48} value")
print(f"{'fine-tune digest':<48} {ft}")
print(f"{'public base digest':<48} {base}")
print(f"{'stolen bytes':<48} {stolen_bytes}")
print(f"{'anonymous registry HTTP':<48} {anon}")
print(f"{'authenticated registry HTTP':<48} {auth_status}")
print(f"{'outsider blocked':<48} {outsider.get('blocked')}")
print(f"{'operator median ms':<48} {operator.get('median_ms')}")
for key, value in got.items():
    print(f"[{'ok' if value else '!!'}] {key}: {value}")

expected = json.loads(labkit.inp("expected/evaluate.json").read_text())
labkit.out("evaluate.json").write_text(json.dumps({"checks": got, "stolen_bytes": stolen_bytes}, indent=2))
diff = [k for k in expected if got.get(k) != expected[k]]
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
