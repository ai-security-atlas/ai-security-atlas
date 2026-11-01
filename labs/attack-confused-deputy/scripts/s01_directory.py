"""Step 1: users, tokens, documents, and one call with the assistant's admin token. No model call.
Run from labs/:
    docker compose run --rm workbench python attack-confused-deputy/scripts/s01_directory.py
"""
import labkit

labkit.banner()

import library as lib  # noqa: E402

page = lib.get("/admin/agent?profile=cdoc-deputy")
names = [t["name"] for t in page["tools"]]
if names != ["cdoc_list", "cdoc_read"]:
    raise SystemExit(f"[!!] cdoc-deputy grants {names}")
print(f"MCP {page['server']} protocol {page['protocol']}")
print("cdoc-deputy tools: " + " ".join(names))
by_name = {t["name"]: t for t in page["tools"]}
print(f"cdoc_read def_sha256 {by_name['cdoc_read']['sha256']}")
print(f"cdoc_read risk {by_name['cdoc_read'].get('risk') or 'blank'}")

for uid, user in lib.USERS.items():
    print(f"user {uid} role {user['role']} scope {user['scope']} token {user['token']}")
for key in ("admin", "public"):
    tok = lib.TOKENS[key]
    print(f"service {key} token {tok['id']} scope {tok['scope']}")
for doc in lib.SPEC["documents"]:
    flag = "yes" if lib.CANARY in doc["body"] else "no"
    print(f"document {doc['id']} acl {doc['acl']} canary {flag}")
for key, text in lib.TASKS.items():
    print(f"canary in task {key}: {'yes' if lib.CANARY in text else 'no'}")
print(f"canary in prompt: {'yes' if lib.CANARY in lib.PROMPT or lib.CANARY in lib.POLICY else 'no'}")

mallory = lib.show("deputy-mallory-board", lib.call("cdoc-deputy", "mallory", "board-notes", "s01-board"))
handbook = lib.show("deputy-mallory-handbook", lib.call("cdoc-deputy", "mallory", "handbook", "s01-handbook"))
scope = lib.USERS["mallory"]["scope"]
acl = lib.DOCS["board-notes"]["acl"]
print(f"counterfactual {scope} on {acl}: {'allow' if lib.allows(scope, acl) else 'deny'}")
if mallory["status"] != 200 or not mallory["canary"] or mallory["authz"] != "skipped":
    raise SystemExit("[!!] the admin token should return board-notes with authz skipped")
if handbook["canary"] or handbook["status"] != 200:
    raise SystemExit("[!!] the handbook read should succeed without the canary")

lib.save("s01.json", {"protocol": page["protocol"], "server": page["server"], "tools": names,
                      "sha256": by_name["cdoc_read"]["sha256"], "mallory": mallory, "handbook": handbook,
                      "counterfactual": "deny"})
