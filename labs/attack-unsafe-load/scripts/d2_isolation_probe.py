"""Step D2: fire the same payload inside the sandbox, then probe what it could reach. Run from labs/:
    docker compose run --rm sandbox python attack-unsafe-load/scripts/d2_isolation_probe.py work/malicious.pt

The load is unsafe on purpose (weights_only=False), so the inert payload runs. The probes
below are separate harness code that runs after the load; the payload never touches the
network. Every probe target is reserved and can never leave the machine:
  canary.invalid (RFC 2606 .invalid TLD) and 192.0.2.1:9 (TEST-NET-1, never routed).
"""
import socket
import sys

import labkit

labkit.banner()

import torch  # noqa: E402

if len(sys.argv) != 2:
    sys.exit("usage: d2_isolation_probe.py <input>")
m = labkit.marker()
m.unlink(missing_ok=True)

print(f"loading {sys.argv[1]} with torch.load(weights_only=False)")
torch.load(labkit.inp(sys.argv[1]), weights_only=False)
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
