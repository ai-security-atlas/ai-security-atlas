"""Step 4: one API record, the audit row, and the same call when the admin token's scope is checked.
No model call. Run from labs/:
    docker compose run --rm workbench python attack-confused-deputy/scripts/s04_trace.py
"""
import labkit

labkit.banner()

import library as lib  # noqa: E402

session = "s04-replay"
skipped = lib.show("replay", lib.call("cdoc-deputy", "mallory", "board-notes", session))
checked = lib.show("checked-admin", lib.call("cdoc-checked", "mallory", "board-notes", session + "-checked"))
scope = lib.USERS["mallory"]["scope"]
acl = lib.DOCS["board-notes"]["acl"]
verdict = "allow" if lib.allows(scope, acl) else "deny"
print(f"counterfactual {scope} on acl {acl}: {verdict}")
rows = lib.get(f"/admin/audit?n=100&session={session}")
hit = [r for r in rows if r.get("kind") == "docs-api" and r.get("doc") == "board-notes" and r.get("authz") == "skipped"]
if not hit:
    raise SystemExit(f"[!!] audit.jsonl has no docs-api row for session {session}")
row = hit[-1]
print(f"audit kind {row['kind']} token {row['token']} principal {row['principal']} "
      f"auth {row['auth']} authz {row['authz']} status {row['status']} doc {row['doc']}")
if row["token"] != lib.TOKENS["admin"]["id"] or row["principal"] != "mallory" or row["status"] != 200:
    raise SystemExit("[!!] the audit row should be the admin token on behalf of mallory")
if checked["status"] != 200 or not checked["canary"] or checked["authz"] != "allow":
    raise SystemExit("[!!] checking the admin token's scope should still allow board-notes")
if skipped["authz"] != "skipped" or verdict != "deny":
    raise SystemExit("[!!] mallory's own scope should deny board-notes")
lib.save("s04.json", {"skipped": skipped, "checked": {"status": checked["status"], "authz": checked["authz"],
                                                      "canary": checked["canary"], "token": checked["token"]},
                      "counterfactual": verdict, "audit_token": row["token"], "audit_principal": row["principal"]})
