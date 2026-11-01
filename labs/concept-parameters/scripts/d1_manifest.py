"""Step D1: verify every file against the pinned sha256 manifest before loading. Run from labs/:
    docker compose run --rm workbench python concept-parameters/scripts/d1_manifest.py
The pinned manifest is assets/pinned_manifest.json (the sha256 of each file of the pinned revision). A folder
that does not match is refused and never loaded. The last row loads the verified snapshot and then registers
Step 4's hook, the way code already running in the serving process could.
"""
import labkit

labkit.banner()

import paramlab as pl  # noqa: E402

clock = pl.Timer()
pin = pl.pinned()["files"]
work = labkit.work()
n = len(pl.PROBES)


def verify(folder):
    got = pl.file_manifest(folder)
    bad = sorted(f for f in set(pin) | set(got) if pin.get(f) != got.get(f))
    return bad, len(got)


rows = []
print(f"{'model folder':<38} {'manifest':<32} {'loaded':<8} canary")
for label, folder in [("pinned snapshot", pl.snapshot()), ("work/edited/ (Step 3)", work / "edited")]:
    if not folder.exists():
        raise SystemExit(f"[!!] {folder} is missing; run Step 3 first")
    bad, files = verify(folder)
    verdict = f"MATCH {files}/{len(pin)}" if not bad else f"MISMATCH {', '.join(bad)}"
    k = None
    if not bad:
        tok, model = pl.load(folder)
        k = sum(map(pl.has_canary, pl.replies(tok, model, pl.PROBES)))
    rows.append({"folder": label, "verdict": "MATCH" if not bad else "MISMATCH", "bad": bad, "loaded": not bad, "k": k})
    print(f"{label:<38} {verdict:<32} {'yes' if not bad else 'REFUSED':<8} {'-' if k is None else f'{k}/{n}'}")

# The hook route: files verified and loaded, then changed in memory.
handle = pl.add_hook(model, pl.delta())
bad, _ = verify(pl.snapshot())
k = sum(map(pl.has_canary, pl.replies(tok, model, pl.PROBES)))
label = "pinned snapshot + hook after load"
print(f"{label:<38} {(f'MATCH {len(pin)}/{len(pin)}' if not bad else 'MISMATCH'):<32} {'yes':<8} {k}/{n}")
rows.append({"folder": label, "verdict": "MATCH" if not bad else "MISMATCH", "bad": bad, "loaded": True, "k": k})
handle.remove()
pl.jdump("manifest_check.json", {"rows": rows, "n": n, "pinned_sha": pin["model.safetensors"]})
refused = [r["folder"].split(" ")[0] for r in rows if not r["loaded"]]
blind = not bad and k > 0
print(f"RESULT the manifest refused {', '.join(refused) or 'nothing'} before load and "
      f"{'passed' if not bad else 'failed'} the hooked process, which printed {pl.CANARY} on {k}/{n}"
      f"{': file integrity says nothing about run time' if blind else ''} ({clock})")
