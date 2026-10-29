"""Step 5: which revision did you actually load? Branches and tags move; a commit sha does not. Run from labs/:
    docker compose run --rm workbench python attack-dependency/scripts/s05_revisions.py

Loads acme/tiny-sentiment with trust_remote_code=True at four revisions, each in a fresh process
(s03_victim_load.py), and records whether the canary marker appeared:
  main, the tag v1.0, then the attacker force-moves v1.0 to the v1.1 commit
  (`git push --force origin v1.0`), then v1.0 again, then the full commit sha your team reviewed.
"code reviewed?" compares the code files at that commit with work/reviewed.json.
"""
import json
import subprocess
import sys

import labkit
import local_hub

labkit.banner()

REPO = "acme/tiny-sentiment"
W = labkit.work()
hub = local_hub.Hub(W / "hub")
reviewed_file = W / "reviewed.json"
if not hub.exists(REPO) or not reviewed_file.exists() or len(hub.log(REPO, "main")) < 2:
    raise SystemExit("[!!] run Steps 1 and 2 first")
reviewed = json.loads(reviewed_file.read_text())
if hub.resolve(REPO, "v1.0") != reviewed["commit"]:  # a rerun after the tag was moved: put it back first
    hub.tag(REPO, "v1.0", reviewed["commit"], force=True)
victim = str(labkit.lab() / "scripts" / "s03_victim_load.py")


def load(rev):
    sha = hub.resolve(REPO, rev)
    ok = all(local_hub.sha256_bytes(hub.show(REPO, sha, f)) == h for f, h in reviewed["code"].items())
    out = subprocess.run([sys.executable, victim, "--revision", rev, "--trust-remote-code"], capture_output=True,
                         text=True, stdin=subprocess.DEVNULL).stdout
    fired = "marker exists: True" in out
    shown = rev if not local_hub.is_sha(rev) else rev[:12] + "... (full sha)"
    print(f"{shown:<28} {sha[:7]:<12} {'yes' if ok else 'NO':<16} {'FIRED' if fired else '-'}")


print(f"{'revision':<28} {'commit':<12} {'code reviewed?':<16} payload")
load("main")
load("v1.0")
moved = hub.tag(REPO, "v1.0", "main", force=True)
print(f"-- attacker: git push --force origin v1.0   (tag v1.0 now -> {moved[:7]})")
load("v1.0")
load(reviewed["commit"])
