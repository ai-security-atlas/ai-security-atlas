"""Step 1: save a benign checkpoint and look inside it before loading anything. Run from labs/:
    docker compose run --rm workbench python attack-unsafe-load/scripts/s01_inspect_benign.py

A .pt file is a ZIP archive. The tensor bytes sit in data/0..3; the structure that ties
them together is data.pkl, a pickle program that torch.load() runs to rebuild the dict.
"""
import io
import pickletools
import zipfile

import labkit

labkit.banner()

import torch  # noqa: E402

torch.manual_seed(0)
model = torch.nn.Sequential(torch.nn.Linear(4, 3), torch.nn.ReLU(), torch.nn.Linear(3, 2))
path = labkit.out("benign.pt")
torch.save(model.state_dict(), path)
print(f"wrote work/{path.name} ({path.stat().st_size} bytes); keys: {list(model.state_dict())}")

z = zipfile.ZipFile(path)
print("\nZIP entries:")
for i in z.infolist():
    if i.filename.endswith(".data/serialization_id"):
        continue
    print(f"  {i.filename:<34} {i.file_size:5d} bytes")
print("  (hidden: .data/serialization_id, random per save)")

pkl = z.read(next(n for n in z.namelist() if n.endswith("/data.pkl")))
print("\npickletools.dis(benign/data.pkl):")
pickletools.dis(io.BytesIO(pkl))

imports = [str(arg) for op, arg, _ in pickletools.genops(pkl) if op.name == "GLOBAL"]
print("\nGLOBAL imports: " + " | ".join(dict.fromkeys(imports)))
