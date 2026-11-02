"""Step 3: five surfaces of one tool call, and which of them anything checks. No model call. Run from labs/:
    docker compose run --rm workbench python system-tools/scripts/s03_surfaces.py
"""
import labkit

labkit.banner()

import stk  # noqa: E402

s01 = stk.load("s01.json")
read = next(t for t in s01["tools"] if t["name"] == "stools-read_file")
inv = next(t for t in s01["tools"] if t["name"] == "stools-get_invoice")
own = stk.call("stools-naive", "stools-get_invoice", {"customer": stk.PRINCIPAL}, "s03")
other = stk.call("stools-naive", "stools-get_invoice", {"customer": "bob"}, "s03")
up = stk.call("stools-naive", "stools-read_file", {"path": "../canary.txt"}, "s03")
desc_check = "none" if read["verbatim"] else "rewritten"
arg_check = "type only" if not read["constraints"] else "schema " + " ".join(read["constraints"])
out_check = "none" if up["canary"] else "filtered"
id_bound = own["row"]["scope"] == f"invoices:{stk.PRINCIPAL}"
auth_check = "none" if other["row"]["status"] == 200 else f"status {other['row']['status']}"
rows = [
    ("description", "tool author", f"{read['chars']} chars, verbatim into context", desc_check),
    ("arguments", "the model", f"path:{read['params'].split(':')[1]}, constraints {' '.join(read['constraints']) or 'none'}", arg_check),
    ("output", "tool + its data", f"out-of-scope text returned as is: {'yes' if up['canary'] else 'no'}", out_check),
    ("identity", "tool config", f"token {own['row']['token']} scope {own['row']['scope']}", "bound to user" if id_bound else "not bound to user"),
    ("authorization", "tool code", f"alice->bob status {other['row']['status']}", auth_check),
]
UNCHECKED = ("none", "type only", "not bound to user")
print(f"{'surface':<14}{'set by':<17}{'what this desk does':<48}check")
for name, by, what, check in rows:
    print(f"{name:<14}{by:<17}{what:<48}{check}")
print(f"path ../canary.txt resolved to {up['row']['resolved']} status {up['row']['status']} "
      f"canary {'yes' if up['canary'] else 'no'}")
print(f"alice asking for bob: token {other['row']['token']} canary {'yes' if other['canary'] else 'no'}")
print(f"surfaces with no security check: {sum(1 for r in rows if r[3] in UNCHECKED)} of {len(rows)}")
stk.save("s03.json", {"rows": [dict(zip(("surface", "set_by", "what", "check"), r)) for r in rows],
                      "traversal": {"resolved": up["row"]["resolved"], "status": up["row"]["status"], "canary": up["canary"]},
                      "other": {"token": other["row"]["token"], "status": other["row"]["status"], "canary": other["canary"]}})
