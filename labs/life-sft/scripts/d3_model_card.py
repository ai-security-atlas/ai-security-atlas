"""Step D3: record what an adapter was trained on, sign the record, and verify it before loading.
Run from labs/:
    docker compose run --rm workbench python life-sft/scripts/d3_model_card.py
The card holds the base repo and revision, the sha256 of the base weights, of the adapter file and of the
training JSONL, and the recipe. It is signed with HMAC-SHA256 under a fixed lab key, a stand-in for a real
signature (OpenSSF model-signing / Sigstore) that needs no network. Writes work/model-card-d0.json.
"""
import hashlib
import hmac
import json
from pathlib import Path

import labkit

labkit.banner()

import tinylm  # noqa: E402

import sftlab as L  # noqa: E402

KEY = b"atlas-lab-demo-key (stand-in for a release signing key)"


def sign(card):
    body = json.dumps({k: v for k, v in card.items() if k != "signature"}, sort_keys=True).encode()
    return hmac.new(KEY, body, hashlib.sha256).hexdigest()


def verify(card, adapter_dir, rows):
    """List of failed checks (empty = OK)."""
    bad = []
    if not hmac.compare_digest(card.get("signature", ""), sign(card)):
        bad.append("signature")
    if tinylm.adapter_sha256(labkit.inp(adapter_dir)) != card["adapter_sha256"]:
        bad.append("adapter sha256")
    if L.dataset_sha256(rows) != card["dataset_sha256"]:
        bad.append("dataset sha256")
    return bad


base_sha = tinylm.sha256(Path(tinylm.fetch(L.BASE)) / "model.safetensors")
card = {"name": "atlas-outfitters-triage d0", "base": L.REPO, "base_revision": L.REV,
        "base_sha256": base_sha, "adapter_sha256": tinylm.adapter_sha256(labkit.inp(L.ADAPTERS[0])),
        "dataset_sha256": L.dataset_sha256(L.mix(0)), "dataset_rows": len(L.mix(0)), "recipe": {**L.TRAIN, "targets": list(L.TRAIN["targets"])}}
card["signature"] = sign(card)
labkit.out("model-card-d0.json").write_text(json.dumps(card, indent=2, sort_keys=True) + "\n")
print("wrote work/model-card-d0.json: base " + L.REV[:7] + f", base weights {base_sha[:12]}, "
      f"adapter {card['adapter_sha256'][:12]}, dataset {card['dataset_sha256'][:12]} ({card['dataset_rows']} rows), "
      f"signature {card['signature'][:12]}")
forged = dict(card, adapter_sha256=tinylm.adapter_sha256(labkit.inp(L.ADAPTERS[20])),
              dataset_sha256=L.dataset_sha256(L.mix(20)))
cases = [
    ("release as built: d0 adapter, mix-d0", card, L.ADAPTERS[0], L.mix(0)),
    ("adapter swapped for d20", card, L.ADAPTERS[20], L.mix(0)),
    ("training file swapped for mix-d20", card, L.ADAPTERS[0], L.mix(20)),
    ("card edited to the d20 hashes, no key", forged, L.ADAPTERS[20], L.mix(20)),
]
res = []
print(f"{'case':<42} result")
for name, c, ad, rows in cases:
    bad = verify(c, ad, rows)
    res.append({"case": name, "failed": bad})
    print(f"{name:<42} {'OK' if not bad else 'REJECT (' + ', '.join(bad) + ')'}")
L.jdump("d3_model_card.json", {"card": card, "cases": res})
