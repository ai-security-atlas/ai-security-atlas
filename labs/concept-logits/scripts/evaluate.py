"""Evaluate: re-measure what each detail level leaks and compare with expected/evaluate.json. Run from labs/:
    docker compose run --rm workbench python concept-logits/scripts/evaluate.py
Ends with exactly "RESULT: REPRODUCED" or "RESULT: MISMATCH (<what differed>)".
"""
import json

import labkit

labkit.banner()

import logitlab  # noqa: E402

P = logitlab.Policy
tok, model = logitlab.load()


def secret(pol):
    got = []
    for s in "AB":
        api = logitlab.LabAPI(tok, model, s, pol, quiet=True)
        r = logitlab.probe_full(api, tok) if pol.detail == "full" else (
            logitlab.probe_topk(api, 20) if pol.detail == "topk" else logitlab.probe_text(api, 20))
        api.close()
        got.append(f"{s}:{r['queries']}q" if r["guess"] == s else (f"{s}:wrong" if r["guess"] else f"{s}:none"))
    return " ".join(got)


def hidden(pol):
    api = logitlab.LabAPI(tok, model, "A", pol, quiet=True)
    h = logitlab.hidden_dim(api, tok)
    api.close()
    return h["dim"] if h["dim"] == model.config.hidden_size else "not found"


def near(pol):
    api = logitlab.LabAPI(tok, model, "A", pol, quiet=True)
    n = sum(1 for x in logitlab.near_dup(api, tok, pol.detail) if x["decided"])
    api.close()
    return n


got = {
    "secret · full": secret(P("full")),
    "secret · topk5": secret(P("topk")),
    "secret · topk5 +scrub": secret(P("topk", scrub=True)),
    "secret · text": secret(P("text")),
    "near-dup originals · full": near(P("full")),
    "near-dup originals · text": near(P("text")),
    "hidden size · full": hidden(P("full")),
    "hidden size · full round=0": hidden(P("full", decimals=0)),
}
labkit.out("evaluate.json").write_text(json.dumps(got, indent=1) + "\n")
expected = json.loads(labkit.inp("expected/evaluate.json").read_text())

print(f"{'condition':<28} {'expected':<15} got")
for cond, want in expected.items():
    print(f"{cond:<28} {str(want):<15} {got.get(cond)}")
diff = [c for c, want in expected.items() if got.get(c) != want]
print("RESULT: REPRODUCED" if not diff else f"RESULT: MISMATCH ({', '.join(diff)})")
