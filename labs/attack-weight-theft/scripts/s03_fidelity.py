"""Step 3: the public base shares the weight blob. The fine-tune digest does not.

    docker compose run --rm workbench python attack-weight-theft/scripts/s03_fidelity.py
"""
import json

import labkit

import theftkit

labkit.banner()

copy_status, _ = theftkit.copy_model(theftkit.BASE, theftkit.BASE_PUSH)
print(f"[ok] POST /api/copy public base HTTP {copy_status} -> {theftkit.BASE_PUSH}")
seconds, last, err = theftkit.push_model(theftkit.BASE_PUSH)
if err:
    print(f"[!!] public base push failed: {err}")
    raise SystemExit(1)
print(f"[ok] pushed public base in {seconds:.1f}s (blobs already stored are not sent again)")

_, _, stolen = theftkit.manifest(theftkit.STOLEN_REPO, theftkit.STOLEN_TAG)
_, _, base = theftkit.manifest(theftkit.BASE_REPO, theftkit.BASE_TAG)

def one(manifest, suffix):
    rows = theftkit.layers(manifest, suffix)
    return rows[0]["digest"] if rows else ""

stolen_weight = one(stolen, ".model")
base_weight = one(base, ".model")
print(f"fine-tune weight {stolen_weight}")
print(f"public base weight {base_weight}")
print(f"[ok] weight blob equals public base: {stolen_weight == base_weight and bool(stolen_weight)}")

_, models = theftkit.tags()
ft = theftkit.digest_of(models.get("models", []), theftkit.MODEL)
base_digest = theftkit.digest_of(models.get("models", []), theftkit.BASE)
print(f"fine-tune model digest {ft}")
print(f"public base model digest {base_digest}")
print(f"[ok] model digest differs from public base: {bool(ft and base_digest and ft != base_digest)}")

stolen_system = [layer["digest"] for layer in theftkit.layers(stolen, ".system")]
base_system = [layer["digest"] for layer in theftkit.layers(base, ".system")]
print(f"fine-tune system layers {', '.join(stolen_system)}")
print(f"public base system layers {', '.join(base_system)}")
private = [d for d in stolen_system if d not in base_system]
print(f"[ok] system layer present only on the fine-tune: {len(private) == 1}")

exfil = json.loads(labkit.out("exfil.json").read_text()) if labkit.out("exfil.json").exists() else {}
canary_layer = ""
for row in exfil.get("layers", {}).get("system", []):
    if row.get("canary"):
        canary_layer = row["digest"]
print(f"[ok] canary layer is the private system layer: {canary_layer in private and bool(canary_layer)}")
print("[note] copying the public GGUF is not the theft. The private artifact is the fine-tune manifest.")

labkit.out("fidelity.json").write_text(json.dumps({
    "weight_equal": stolen_weight == base_weight and bool(stolen_weight),
    "digest_differs": ft != base_digest and bool(ft),
    "stolen_weight": stolen_weight,
    "base_weight": base_weight,
    "fine_tune_digest": ft,
    "base_digest": base_digest,
    "private_system": private,
    "base_push_s": round(seconds, 3),
}, indent=2))
print("[ok] wrote fidelity.json")
