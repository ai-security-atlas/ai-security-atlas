"""The Atlas Widgets checkout service, for LAB-19 (a helper module; not run by itself). Fictional and local:
it prices an order in memory and returns a dict; nothing is charged, stored or sent anywhere.

Two designs of the same staff discount (40 %):
  checkout(account, total, code=..., design="code")     the original design: whoever enters the staff code
                                                        gets the discount (the code is a bearer secret, and
                                                        it was pasted into the assistant's system prompt)
  checkout(account, total, design="account")            D3: no code exists; the service looks up the signed-in
                                                        account and applies the discount to staff accounts only.
                                                        A code is ignored, whatever the assistant said.
Codes are compared like many real checkouts do: case, spaces and dashes are ignored.
"""
import leak

STAFF_RATE = 0.40
ACCOUNTS = {"guest-1042": "customer", "sam.ortiz": "staff"}   # fictional accounts of the lab


def checkout(account, total, code=None, design="code", staff_code=None) -> dict:
    role = ACCOUNTS.get(account, "unknown")
    if design == "code":
        ok = bool(code) and leak.norm(code) == leak.norm(staff_code or "")
        why = "staff code accepted" if ok else ("no code" if not code else "code not recognised")
    else:
        ok = role == "staff"
        why = f"account role {role}" + ("" if not code else "; codes are not accepted")
    pay = round(total * (1 - STAFF_RATE), 2) if ok else total
    return {"account": account, "role": role, "design": design, "code": code, "discount": ok, "total": total,
            "pay": pay, "why": why}
