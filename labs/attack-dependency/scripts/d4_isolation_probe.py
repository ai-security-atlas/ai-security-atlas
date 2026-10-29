"""Step D4: run the same remote code inside the sandbox, then probe what it could reach. Run from labs/:
    docker compose run --rm sandbox python attack-dependency/scripts/d4_isolation_probe.py --revision main

The sandbox is LAB-01's isolation service (no network, read-only root and checkout, no
capabilities, a tmpfs /work that vanishes with --rm). The load is unsafe on purpose
(trust_remote_code=True on the tampered main), so the inert payload runs. The probes below are
separate harness code that runs after the load; the payload never touches the network. Every
probe target is reserved and can never leave the machine: canary.invalid (RFC 2606) and
192.0.2.1:9 (TEST-NET-1, never routed).
"""
import argparse
import os
import socket
from pathlib import Path

# Set before `import labkit`, which imports transformers (it reads HF_MODULES_CACHE once, at import):
# transformers copies repo code into this folder before importing it; keep it in this lab's work dir.
os.environ["HF_MODULES_CACHE"] = str(Path(os.environ.get("ATLAS_WORK") or Path(__file__).resolve().parents[1] / "work")
                                     / "hf_modules")

import labkit  # noqa: E402
import local_hub  # noqa: E402

labkit.banner()

W = labkit.work()                                        # /work (tmpfs) in the sandbox
os.environ["ATLAS_WORK"] = str(W)

ap = argparse.ArgumentParser()
ap.add_argument("--revision", required=True)
rev = ap.parse_args().revision

hub = local_hub.Hub(labkit.inp("work/hub"), snapshots_root=W / "snapshots")  # read the hub, write snapshots to /work
m = labkit.marker()
m.unlink(missing_ok=True)
folder, sha = hub.snapshot("acme/tiny-sentiment", rev)

from transformers import AutoModelForSequenceClassification  # noqa: E402

print(f"from_pretrained(<snapshot of {rev} = {sha[:7]}>, trust_remote_code=True)")
AutoModelForSequenceClassification.from_pretrained(folder, trust_remote_code=True)
print(f"marker in sandbox: {m.exists()} ({m})")


def err(e):
    return f"{type(e).__name__} {e.strerror or e}" if isinstance(e, OSError) else f"{type(e).__name__} {e}"


def probe_dns():
    try:
        return f"resolved {socket.gethostbyname('canary.invalid')}"
    except OSError as e:
        return f"{type(e).__name__} (no network): {e}"


def probe_egress():
    try:
        socket.create_connection(("192.0.2.1", 9), timeout=3).close()
        return "connected"
    except OSError as e:
        return err(e)


def probe_ro_write():
    try:
        (labkit.lab() / "work" / "probe.txt").write_text("x")
        return "write succeeded"
    except OSError as e:
        return err(e)


print(f"dns canary.invalid: {probe_dns()}")
print(f"egress 192.0.2.1:9: {probe_egress()}")
print(f"write to /labs: {probe_ro_write()}")
