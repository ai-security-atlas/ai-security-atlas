"""spl: the shared code of LAB-58 adapt-softprompt (imported by the step scripts).

* A small, fictional support-ticket routing task: each message goes to one of four queues.
  TRAIN and HELDOUT are disjoint, hand-written rows (no real customer data).
* load(): SmolLM2-135M-Instruct from tinylm (pinned revision), fp32, frozen.
* soft(): wrap the frozen model with a peft PromptTuningConfig (learned input embeddings).
* prefix(): wrap it with a peft PrefixTuningConfig (learned key/value prefixes at every layer).
* train(): a seeded Adam loop; the loss is the cross-entropy of the queue word only.
* accuracy(): constrained scoring (argmax over the four queue words at the answer position).
* route(): the stub router. It logs the inert canary for every ticket it sends to the wrong queue,
  so a wrong prompt is visible in the output and nothing else happens.
Everything runs locally in the workbench container.
"""
import hashlib
import json

import torch

torch.set_num_threads(min(4, torch.get_num_threads()))  # other jobs share the test machine; see README

import tinylm  # noqa: E402

MODEL = "smollm2-135m"
CANARY = "ATLAS-CANARY-s0ft"
N_VIRTUAL = 8
SEED = 0
STEPS = 45         # full-batch Adam steps for every training run
LR_SOFT = 0.3      # soft prompt (Steps 2 and 5); picked from 0.03/0.1/0.3, see README Step 4
LR_PREFIX = 0.03   # prefix (Step 4); picked from 0.01/0.03/0.1
TEMPLATE = "Support message: {msg}\nQueue:"
QUEUES = ["billing", "shipping", "account", "other"]
SWAP = {"billing": "shipping", "shipping": "billing", "account": "account", "other": "other"}
INSTRUCTION = ("Route each support message to one queue: billing (charges, refunds, invoices), "
               "shipping (deliveries, parcels, tracking), account (login, password, profile) "
               "or other (anything else).\n")

TRAIN = [
    ("I was charged twice for my order", "billing"), ("Please refund the extra fee on my card", "billing"),
    ("My invoice shows the wrong amount", "billing"), ("Why did my subscription price go up", "billing"),
    ("Can I get a receipt for last month", "billing"), ("The payment failed but money left my account", "billing"),
    ("Cancel the automatic renewal charge", "billing"), ("I need a copy of my VAT invoice", "billing"),
    ("You billed me after I cancelled", "billing"), ("The discount code was not applied to my bill", "billing"),
    ("My parcel has not arrived yet", "shipping"), ("The tracking number does not work", "shipping"),
    ("The box was delivered to the wrong address", "shipping"), ("When will my package ship", "shipping"),
    ("The courier left the parcel outside in the rain", "shipping"), ("Can you deliver on Saturday", "shipping"),
    ("My order is stuck at the depot", "shipping"), ("The delivery is two weeks late", "shipping"),
    ("I want to change the delivery address", "shipping"), ("The package arrived damaged", "shipping"),
    ("I cannot log in to my account", "account"), ("Reset my password please", "account"),
    ("How do I change the email on my profile", "account"), ("My account is locked after three tries", "account"),
    ("I never got the verification code", "account"), ("Please delete my user profile", "account"),
    ("The two-factor prompt keeps failing", "account"), ("I want to change my username", "account"),
    ("Someone else is signed in to my account", "account"), ("The login page says my password expired", "account"),
    ("Do you have a store in Lisbon", "other"), ("What are your opening hours", "other"),
    ("I love the new design of the app", "other"), ("Is the blue jacket available in large", "other"),
    ("Can I suggest a new feature", "other"), ("Do you sponsor local football teams", "other"),
    ("Which charger fits this lamp", "other"), ("Are you hiring for summer jobs", "other"),
    ("What is the warranty on the kettle", "other"), ("Do you sell gift wrapping paper", "other"),
]
HELDOUT = [
    ("There is a charge I do not recognise on my statement", "billing"), ("Refund my last payment", "billing"),
    ("The bill total does not match the cart", "billing"), ("I paid but the order says unpaid", "billing"),
    ("Stop charging my card every month", "billing"), ("Send me the invoice for order 4471", "billing"),
    ("Where is my delivery", "shipping"), ("The parcel tracking has not updated in days", "shipping"),
    ("My package went to my neighbour", "shipping"), ("How long does shipping to Canada take", "shipping"),
    ("The courier never rang the bell", "shipping"), ("Half of my order is missing from the box", "shipping"),
    ("I forgot my password", "account"), ("I cannot sign in with my phone", "account"),
    ("Update the phone number on my profile", "account"), ("My account was suspended", "account"),
    ("The verification email never came", "account"), ("Close my account permanently", "account"),
    ("Do you have a shop near the station", "other"), ("Is the café open on Sunday", "other"),
    ("Your new logo looks great", "other"), ("Does the backpack come in green", "other"),
    ("Can I bring my dog into the store", "other"), ("What batteries does the remote use", "other"),
]


def load(download=False):
    """(tokenizer, frozen base model). download=True fetches the pinned snapshot (Step 1)."""
    return tinylm.load(MODEL, download)


def queue_ids(tok):
    """First token id of ' <queue>' for each queue (all four are single tokens; checked in Step 1)."""
    return [tok(" " + q, add_special_tokens=False)["input_ids"][0] for q in QUEUES]


def encode(tok, msg, instruction=False):
    text = (INSTRUCTION if instruction else "") + TEMPLATE.format(msg=msg)
    return tok(text, add_special_tokens=False)["input_ids"]


def soft(model, n=N_VIRTUAL, seed=SEED):
    from peft import PromptTuningConfig, get_peft_model
    torch.manual_seed(seed)
    cfg = PromptTuningConfig(task_type="CAUSAL_LM", num_virtual_tokens=n)
    return get_peft_model(model, cfg)


def prefix(model, n=N_VIRTUAL, seed=SEED):
    from peft import PrefixTuningConfig, get_peft_model
    torch.manual_seed(seed)
    cfg = PrefixTuningConfig(task_type="CAUSAL_LM", num_virtual_tokens=n)
    return get_peft_model(model, cfg)


def trainable(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def _batch(tok, rows, instruction=False):
    ids = [encode(tok, m, instruction) for m, _ in rows]
    L = max(len(x) for x in ids)
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    inp = torch.full((len(ids), L), pad, dtype=torch.long)
    att = torch.zeros((len(ids), L), dtype=torch.long)
    for i, x in enumerate(ids):  # right padding: every row keeps the positions it has when sent alone
        inp[i, :len(x)] = torch.tensor(x)
        att[i, :len(x)] = 1
    return inp, att


def logits_last(model, tok, rows, instruction=False):
    """Logits at each row's last real token. A soft prompt adds its rows in front, so the output is longer."""
    inp, att = _batch(tok, rows, instruction)
    out = model(input_ids=inp, attention_mask=att)
    last = out.logits.shape[1] - inp.shape[1] + att.sum(1) - 1
    return out.logits[torch.arange(len(rows)), last, :]


def train(model, tok, rows, steps=STEPS, lr=0.03, seed=SEED, labels=None, log=None):
    """Adam on the trainable (peft) parameters; loss = CE of the queue word. Returns the loss trace."""
    torch.manual_seed(seed)
    qid = queue_ids(tok)
    gold = torch.tensor([qid[QUEUES.index((labels or {}).get(q, q))] for _, q in rows])
    opt = torch.optim.Adam([p for p in model.parameters() if p.requires_grad], lr=lr)
    trace = []
    for s in range(steps):
        loss = torch.nn.functional.cross_entropy(logits_last(model, tok, rows), gold)
        opt.zero_grad()
        loss.backward()
        opt.step()
        trace.append(round(loss.item(), 4))
        if log and (s == 0 or (s + 1) % 10 == 0):
            log(s + 1, trace[-1])
    return trace


@torch.no_grad()
def predict(model, tok, rows, instruction=False):
    qid = queue_ids(tok)
    lg = logits_last(model, tok, rows, instruction)[:, qid]
    return [QUEUES[i] for i in lg.argmax(-1).tolist()]


def accuracy(preds, rows, labels=None):
    gold = [(labels or {}).get(q, q) for _, q in rows]
    return sum(p == g for p, g in zip(preds, gold))


def route(msg, gold, pred):
    """Stub router: prints where the ticket went; a ticket sent to the wrong queue logs the canary."""
    line = f"[router] {gold:8s} -> {pred:8s} {msg!r}"
    if pred != gold:
        line += f" -> {CANARY}"
    return line


def router_log(rows, preds, show=4):
    """Print the misrouted tickets (at most `show`) and return how many fired the canary."""
    lines = [route(m, g, q) for (m, g), q in zip(rows, preds)]
    bad = [x for x in lines if CANARY in x]
    for x in bad[:show]:
        print("  " + x)
    if len(bad) > show:
        print(f"  ... ({len(bad) - show} more)")
    print(f"router: {len(bad)}/{len(rows)} held-out tickets misrouted, canary {CANARY} logged for each")
    return len(bad)


def soft_vectors(model):
    """The learned (n x hidden) soft-prompt matrix of a PromptTuning peft model."""
    return model.get_prompt_embedding_to_save("default").detach().clone()


def tensor_sha256(t):
    return hashlib.sha256(t.contiguous().numpy().tobytes()).hexdigest()


def nearest_tokens(tok, emb_table, vecs, k=1):
    """Nearest vocabulary rows by cosine, plus the Euclidean distance to that row."""
    e = torch.nn.functional.normalize(emb_table, dim=-1)
    v = torch.nn.functional.normalize(vecs, dim=-1)
    cos = v @ e.T
    top = cos.topk(k, dim=-1)
    out = []
    for i in range(vecs.shape[0]):
        j = top.indices[i, 0].item()
        out.append((tok.convert_ids_to_tokens(j), round(top.values[i, 0].item(), 3),
                    round((vecs[i] - emb_table[j]).norm().item(), 3)))
    return out


def save_json(path, obj):
    path.write_text(json.dumps(obj, indent=1))


# ---- acceptance gate (Step D2 and Evaluate) ----
GATE_TOTAL = 16      # of 24 held-out rows (two thirds)
GATE_PER_QUEUE = 3   # of 6 rows per queue (half)


def attach(base, d):
    """Load a saved peft prompt (soft or prefix) onto a freshly loaded base model."""
    from peft import PeftModel
    return PeftModel.from_pretrained(base, str(d))


def gate(preds, rows=None):
    """Acceptance rule: total >= GATE_TOTAL and every queue >= GATE_PER_QUEUE correct."""
    rows = rows or HELDOUT
    total = accuracy(preds, rows)
    per = {q: sum(p == g for p, (_, g) in zip(preds, rows) if g == q) for q in QUEUES}
    return total, per, total >= GATE_TOTAL and min(per.values()) >= GATE_PER_QUEUE


def as_text(tok, base, vecs):
    """Replace each learned vector by its nearest token row; return (text, held-out correct)."""
    table = base.get_input_embeddings().weight.detach()
    near = nearest_tokens(tok, table, vecs)
    proj = soft(base)
    with torch.no_grad():
        proj.prompt_encoder["default"].embedding.weight.copy_(table[[tok.convert_tokens_to_ids(n[0]) for n in near]])
    text = tok.convert_tokens_to_string([n[0] for n in near])
    return text, accuracy(predict(proj, tok, HELDOUT), HELDOUT)
