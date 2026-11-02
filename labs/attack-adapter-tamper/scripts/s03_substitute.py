"""Step 3: an attacker with push access replaces the adapter under the same name.
Run from labs/:
    docker compose run --rm workbench python attack-adapter-tamper/scripts/s03_substitute.py
The new files are safetensors plus an adapter_config.json whose base binding and
target_modules differ from the reviewed tag. Requires Step 2's hub.
"""
import json
import shutil

import labkit

labkit.banner()

import desk  # noqa: E402

dirs = desk.hub_dirs()
if not dirs["hub"].exists():
    raise SystemExit("[!!] missing work/hub: run Step 2 first")
shutil.rmtree(dirs["attacker"].parent, ignore_errors=True)
shutil.rmtree(dirs["v1"], ignore_errors=True)
shutil.rmtree(dirs["main"], ignore_errors=True)
desk.git("clone", "-q", str(dirs["hub"]), str(dirs["attacker"]))
atk = dirs["attacker"]
src = labkit.inp(desk.SUBSTITUTED)
for name in ("adapter_config.json", "adapter_model.safetensors"):
    shutil.copy(src / name, atk / name)
desk.git("add", "-A", cwd=atk)
desk.git("commit", "-q", "-m", "refresh lantern-desk weights", cwd=atk, who="lantern-ci")
desk.git("push", "-q", "origin", "main", cwd=atk)
print("attacker push is a local path:")
print(f"  remote {desk.git('remote', 'get-url', 'origin', cwd=atk)}")
print("\n$ git log --oneline main   (commit ids differ on every run)")
print(desk.git("log", "--oneline", "main", cwd=dirs["hub"]))
print("\n$ git diff --stat v1.0 main")
print(desk.git("diff", "--stat", "v1.0", "main", cwd=dirs["hub"]))

old = desk.binding(desk.read_cfg(labkit.inp(desk.REVIEWED)))
new = desk.binding(desk.read_cfg(atk))
print(f"\n{'field':<28} {'v1.0 reviewed':<42} main")
for key in ("base", "revision", "targets"):
    print(f"{key:<28} {old[key]:<42} {new[key]}")

desk.git("clone", "-q", "--branch", "v1.0", str(dirs["hub"]), str(dirs["v1"]))
desk.git("clone", "-q", str(dirs["hub"]), str(dirs["main"]))
print("\n[ok] victim clones: work/victim-v1 (tag v1.0) and work/victim-main (the branch a client tracks)")
print(f"  v1.0 safetensors {desk.file_hashes(dirs['v1'])['adapter_model.safetensors'][:12]}")
print(f"  main safetensors {desk.file_hashes(dirs['main'])['adapter_model.safetensors'][:12]}")
labkit.out("substitute.json").write_text(json.dumps({"v1": old, "main": new}, indent=1) + "\n")
