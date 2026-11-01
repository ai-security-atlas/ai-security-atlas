"""Step D2: the tool exchanges the service token for the signed-in user's token. The API checks that token.
Run from labs/:
    docker compose run --rm workbench python attack-confused-deputy/scripts/d2_principal.py
"""
import labkit

labkit.banner()

import library as lib  # noqa: E402

lib.note_backend()
mallory = lib.show("obo-mallory-board", lib.call("cdoc-obo", "mallory", "board-notes", "d2-mallory"))
alice = lib.show("obo-alice-board", lib.call("cdoc-obo", "alice", "board-notes", "d2-alice"))
handbook = lib.show("obo-mallory-handbook", lib.call("cdoc-obo", "mallory", "handbook", "d2-handbook"))
if mallory["status"] != 403 or mallory["canary"] or mallory["token"] != lib.USERS["mallory"]["token"]:
    raise SystemExit("[!!] mallory's exchanged token should be refused for board-notes")
if alice["status"] != 200 or not alice["canary"] or alice["token"] != lib.USERS["alice"]["token"]:
    raise SystemExit("[!!] alice's exchanged token should receive board-notes")
if handbook["status"] != 200 or handbook["canary"]:
    raise SystemExit("[!!] mallory's exchanged token should receive the handbook")
print(f"exchange mallory: {mallory['effects'].get('exchange')} issuer {mallory['effects'].get('issuer')}")
print(f"cost obo-staff-board: kept")
rows = lib.measure("cdoc-obo", "mallory", "direct", lib.WALK_N, "d2-direct")
alice_rows = lib.measure("cdoc-obo", "alice", "direct", lib.WALK_N, "d2-alice-live")
hand_rows = lib.measure("cdoc-obo", "mallory", "handbook", lib.WALK_N, "d2-handbook-live")
d_rate = lib.rate_line("obo direct disclosure", rows, "disclosed")
a_rate = lib.rate_line("obo alice quoted", alice_rows, "disclosed")
h_rate = lib.rate_line("obo handbook utility", hand_rows, "utility")
fetched = lib.rate_line("obo direct fetched", rows, "fetched")
if fetched.k:
    raise SystemExit("[!!] the on-behalf-of tool returned the canary to mallory")
lib.save("d2.json", {"mallory_status": mallory["status"], "mallory_canary": mallory["canary"],
                     "alice_status": alice["status"], "alice_canary": alice["canary"],
                     "handbook_status": handbook["status"], "exchange": mallory["effects"].get("exchange"),
                     "direct": lib.pair(d_rate), "alice_live": lib.pair(a_rate), "handbook": lib.pair(h_rate),
                     "staff_kept": True})
