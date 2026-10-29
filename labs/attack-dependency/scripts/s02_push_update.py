"""Step 2: someone with push access ships "v1.1", a routine-looking code change. Run from labs/:
    docker compose run --rm workbench python attack-dependency/scripts/s02_push_update.py

The attacker (a leaked CI token, here committing as acme-ci) adds module-level lines to
modeling_tinysent.py on main. The lines are the lab's inert payload, labkit.INERT_CODE, copied
verbatim: it writes work/canary-marker.txt and prints the canary. Nothing is executed here; the
code runs only when a victim imports the module (Step 3). The weights are not touched.
"""
import labkit
import local_hub

labkit.banner()

REPO = "acme/tiny-sentiment"
W = labkit.work()
hub = local_hub.Hub(W / "hub")
if not hub.exists(REPO) or hub.log(REPO, "main")[0][2] != "publish tiny-sentiment v1.0":
    raise SystemExit("[!!] run Step 1 (s01_hub_publish.py) first; it resets the hub")

ANCHOR = "from .configuration_tinysent import TinySentConfig\n"
modeling = hub.show(REPO, "v1.0", "modeling_tinysent.py").decode()
assert modeling.count(ANCHOR) == 1
# Inserted at module level, so it runs on import. The body is labkit.INERT_CODE, unmodified.
injected = "\n# v1.1: warm the byte table at import time\n" + labkit.INERT_CODE
modeling = modeling.replace(ANCHOR, ANCHOR + injected)
assert labkit.INERT_CODE in modeling

card = hub.show(REPO, "v1.0", "README.md").decode().replace("# acme/tiny-sentiment", "# acme/tiny-sentiment (v1.1)")
sha = hub.push(REPO, {"modeling_tinysent.py": modeling, "README.md": card},
               "v1.1: cache the byte table at import", who="acme-ci")
print(f"[ok] acme-ci pushed v1.1 to main: {sha}")

print("\n$ git log --format='%h %cn %s' main")
for short, who, subject in hub.log(REPO, "main"):
    print(f"{short} {who:<8} {subject}")

print("\n$ git diff --stat v1.0 main")
print(hub.diff(REPO, "v1.0", "main", stat=True))

print("\n$ git diff v1.0 main -- modeling_tinysent.py")
for line in hub.diff(REPO, "v1.0", "main", "modeling_tinysent.py").splitlines()[4:]:
    print(line if len(line) <= 110 else line[:107] + "...")
print("\nweights unchanged:", hub.show(REPO, "v1.0", "model.safetensors") == hub.show(REPO, "main", "model.safetensors"))
