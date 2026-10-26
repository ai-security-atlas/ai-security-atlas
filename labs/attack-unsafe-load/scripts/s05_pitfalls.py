"""Step 5: four ways people reopen the hole that weights_only=True closed. Run from labs/:
    docker compose run --rm workbench python attack-unsafe-load/scripts/s05_pitfalls.py

The marker is deleted before each block, so "fired" always means "fired in this block".
"""
import os

import labkit

labkit.banner()

import torch  # noqa: E402
import torch.serialization as ts  # noqa: E402
from safetensors.torch import save_file  # noqa: E402

benign, malicious = labkit.inp("work/benign.pt"), labkit.inp("work/malicious.pt")
m = labkit.marker()


def block(title, fn):
    m.unlink(missing_ok=True)
    print(f"\n{title}")
    try:
        fn()
    except Exception as e:
        print(f"    raised {type(e).__name__}")
    print("    -> [payload] fired" if m.exists() else "    -> payload did not fire")


def inspect():
    # Lists the globals the default loader would reject, without running anything.
    print(f"    benign    {ts.get_unsafe_globals_in_checkpoint(benign)}")
    print(f"    malicious {ts.get_unsafe_globals_in_checkpoint(malicious)}")


def allowlist_exec():
    # Exactly what the Step 4 error message suggests.
    with ts.safe_globals([exec]):
        torch.load(malicious)


def env_override():
    # A wrapper script or CI job that sets this turns every default load back into weights_only=False.
    os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"
    try:
        torch.load(malicious)
    finally:
        del os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"]


def convert():
    # "Just convert it to safetensors": the conversion itself has to load the pickle first.
    sd = torch.load(malicious, weights_only=False)
    save_file(dict(sd), labkit.out("converted.safetensors"))
    print("    wrote work/converted.safetensors (the file is clean; the converter host was not)")


block("(A) inspect first: torch.serialization.get_unsafe_globals_in_checkpoint()", inspect)
block("(B) follow the error's advice: with torch.serialization.safe_globals([exec])", allowlist_exec)
block("(C) TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1 set by a wrapper, then torch.load(f)", env_override)
block("(D) convert to safetensors with torch.load(f, weights_only=False)", convert)
m.unlink(missing_ok=True)
