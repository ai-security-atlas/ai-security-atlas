"""Shared helpers for LAB-43 attack-sponge (imported by the step scripts; not run directly).

Victim: the plain tinylm SmolLM2-135M-Instruct (no guard adapter), fp32, CPU, greedy decoding.
Two attack levers, matching the node's two access profiles:

* A01 (black-box, output-query access): tokenizer amplification. Text built from rare Unicode,
  combining marks, emoji ZWJ sequences and mixed scripts turns into far more tokens per character
  than plain English, so the same character budget buys far more prefill compute. The corpus lives
  in assets/texts.json; the tokenizers are the victim's, Qwen2.5's and GPT-2's (pinned revisions).
* A03 (white-box): a GCG-style search (one-hot gradient, same machinery as LAB-21) over a
  20-token suffix appended to an ordinary request, with an Engorgio-style objective: suppress the
  end-of-sequence token (EOS) at every position of the reply the model would naturally give, so
  greedy generation never stops and runs to max_new_tokens.

The request carries the fixed, inert canary CANARY, so every prompt and reply in this lab is
traceable to the lab. Success is measured in code: generation either reaches the token cap or not.
"""
import json
import math
import resource
import time

import torch

import labkit
import tinylm

P = json.loads(labkit.inp("assets/texts.json").read_text())
CANARY = "ATLAS-CANARY-spn1"
if CANARY not in P["request"]:
    raise SystemExit("[!!] assets/texts.json request was changed; restore it with: git checkout -- attack-sponge/assets")
SYSTEM = P["system"]
REQUEST = P["request"]
VICTIM = "smollm2-135m"
SECOND = "smollm2-360m"
N_SUFFIX = 8                       # small enough that filler alone does not break stopping (measured)
CAP = 128                          # max_new_tokens the lab measures against (the hard ceiling)
INIT = " " + "x " * (N_SUFFIX - 1) + "x"    # ' x x ... x' (8 tokens); the model still stops with it
JUNK_SWEEP = (1, 2, 4, 8, 20)      # filler-token counts Step 3 sweeps to locate the fragility threshold

# Tokenizer-only fetches (no model weights): pinned revisions, tokenizer files only.
TOKENIZERS = {
    "smollm2": (tinylm.MODELS["smollm2-135m"][0], tinylm.MODELS["smollm2-135m"][1]),
    "qwen2.5": (tinylm.MODELS["qwen2.5-0.5b"][0], tinylm.MODELS["qwen2.5-0.5b"][1]),
    "gpt2": ("gpt2", "607a30d783dfa663caf39e06633721c8d4cfcd7e"),
}
TOK_PATTERNS = ["tokenizer*.json", "vocab.json", "merges.txt", "*.json"]


def load(name=VICTIM):
    return tinylm.load(name)


def pinned():
    return json.loads(labkit.inp("assets/sponge.json").read_text())


def load_tokenizer(name):
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer
    repo, rev = TOKENIZERS[name]
    path = snapshot_download(repo, revision=rev, allow_patterns=TOK_PATTERNS, local_files_only=True)
    return AutoTokenizer.from_pretrained(path)


def fetch_tokenizer(name):
    from huggingface_hub import snapshot_download
    repo, rev = TOKENIZERS[name]
    return snapshot_download(repo, revision=rev, allow_patterns=TOK_PATTERNS, local_files_only=False)


# ---------------------------------------------------------------- generation and timing
def cpu_seconds():
    r = resource.getrusage(resource.RUSAGE_SELF)
    return r.ru_utime + r.ru_stime


def generate(tok, model, user, max_new_tokens=CAP, system=SYSTEM):
    """Greedy generate; returns n_in, n_out, stopped (True when EOS ended generation), text.
    Times wall clock and CPU seconds around the whole call."""
    enc = tinylm.prompt_ids(tok, user, system=system)
    n_in = enc["input_ids"].shape[1]
    w0, c0 = time.perf_counter(), cpu_seconds()
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False,
                             pad_token_id=tok.eos_token_id)
    wall, cpu = time.perf_counter() - w0, cpu_seconds() - c0
    n_out = out.shape[1] - n_in
    return {"n_in": n_in, "n_out": int(n_out), "stopped": n_out < max_new_tokens,
            "reply": tok.decode(out[0, n_in:], skip_special_tokens=True).strip(),
            "wall_s": wall, "cpu_s": cpu}


def prefill(tok, model, text, reps=1):
    """Timed prefill (one forward pass, no generation): median wall ms and CPU ms over reps."""
    ids = tok(text, add_special_tokens=False, return_tensors="pt")
    walls, cpus = [], []
    for _ in range(reps):
        w0, c0 = time.perf_counter(), cpu_seconds()
        with torch.no_grad():
            model(input_ids=ids["input_ids"], attention_mask=ids["attention_mask"])
        walls.append((time.perf_counter() - w0) * 1000)
        cpus.append((cpu_seconds() - c0) * 1000)
    walls.sort()
    return {"tokens": int(ids["input_ids"].shape[1]), "wall_ms_med": walls[len(walls) // 2],
            "wall_ms_all": [round(w, 1) for w in walls], "cpu_ms": round(sum(cpus) / len(cpus), 1)}


# ---------------------------------------------------------------- the EOS-suppression objective
def template(tok):
    """(before, after): the chat template around the place where the suffix goes."""
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": REQUEST + "{optim_str}"}]
    s = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    before, after = s.split("{optim_str}")
    return before, after


def enc(tok, text):
    return tok(text, add_special_tokens=False)["input_ids"]


def parts(tok):
    before, after = template(tok)
    return enc(tok, before), enc(tok, after)


def greedy_reply_ids(tok, model, user, max_new_tokens=CAP, system=SYSTEM):
    """The greedy reply to `user`, as token ids ending in EOS (or reaching the cap)."""
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    ids = tok.apply_chat_template(msgs, add_generation_prompt=True)
    if hasattr(ids, "keys") and "input_ids" in ids:
        ids = ids["input_ids"]
    ids = torch.tensor([list(ids)])
    with torch.no_grad():
        out = model.generate(input_ids=ids, attention_mask=torch.ones_like(ids), max_new_tokens=max_new_tokens,
                             do_sample=False, pad_token_id=tok.eos_token_id)
    return out[0, ids.shape[1]:].tolist()


def clean_reply_ids(tok, model):
    """The greedy reply to the clean request, ending in EOS. The teacher-forced stop trajectory."""
    return greedy_reply_ids(tok, model, REQUEST)


def _eos_id(model):
    return model.config.eos_token_id or 0


def eos_margins(model, before, suffixes, after, traj):
    """By how many logits the best non-stop token beats the stop token at every teacher-forced
    position, for each suffix row (B x T). Greedy decoding emits EOS exactly when this margin is
    negative, so the attack wants it positive at every position. Also returns p(EOS) for display."""
    if isinstance(suffixes, list):
        suffixes = torch.tensor([list(suffixes)], dtype=torch.long)   # [] -> one empty suffix row
    B = suffixes.shape[0]
    pre = torch.tensor(before).repeat(B, 1)
    post = torch.tensor(after + traj[:-1]).repeat(B, 1)
    ids = torch.cat([pre, suffixes, post], 1)
    T = len(traj)
    eos = _eos_id(model)
    with torch.no_grad():
        z = model.lm_head(model.model(input_ids=ids).last_hidden_state[:, -T:])  # B x T x V
        p = torch.softmax(z, -1)[:, :, eos]
        z_eos = z[:, :, eos].clone()          # a view would see the -inf mutation below
        z[:, :, eos] = -float("inf")
        margin = z.max(-1).values - z_eos
    return margin, p  # B x T each


def margin_loss(model, before, suffixes, after, traj):
    """Engorgio-style objective (mean over the trajectory): softplus of the negative margin, so
    every position where the stop token still wins keeps pushing. Lower = the model wants to
    stop less at every point of the trajectory."""
    margin, _ = eos_margins(model, before, suffixes, after, traj)
    return torch.nn.functional.softplus(-margin / 2, beta=2).mean(1)


def onehot_grad(model, before, suffix, after, traj):
    """(loss, grad): the margin loss and its gradient over the one-hot suffix matrix."""
    emb = model.get_input_embeddings()
    oh = torch.nn.functional.one_hot(torch.tensor(suffix), emb.num_embeddings).float().requires_grad_()
    e = torch.cat([emb(torch.tensor([before])), (oh @ emb.weight).unsqueeze(0),
                   emb(torch.tensor([after + traj[:-1]]))], 1)
    T = len(traj)
    z = model.lm_head(model.model(inputs_embeds=e).last_hidden_state[:, -T:])  # 1 x T x V
    eos = _eos_id(model)
    z_eos = z[0, :, eos].clone()               # a view would see the -inf mutation below
    z[0, :, eos] = -float("inf")
    margin = z.max(-1).values - z_eos
    loss = torch.nn.functional.softplus(-margin / 2, beta=2).mean()
    (g,) = torch.autograd.grad(loss, [oh])
    return loss.item(), g


def banned_ids(tok):
    """Tokens the search may not use: non-ASCII ones and any token that spells a piece of the
    canary, so the canary text never appears in the suffix itself (it already sits in the request)."""
    from nanogcg.utils import get_nonascii_toks
    canary = CANARY.lower()
    frag = [i for i in range(len(tok)) if len(t := tok.decode([i]).strip().lower()) >= 2 and t in canary]
    return torch.unique(torch.cat([get_nonascii_toks(tok), torch.tensor(frag, dtype=torch.long)]))


def filter_candidates(tok, cands):
    """nanogcg's filter_ids: keep only candidates whose text survives decode -> encode unchanged."""
    keep = []
    for ids in cands.tolist():
        text = tok.decode(ids)
        if tok(text, add_special_tokens=False)["input_ids"] == ids:
            keep.append(ids)
    return torch.tensor(keep, dtype=torch.long)


def sample_candidates(tok, grad, suffix, width, topk, banned, gen):
    """`width` candidates, each replacing one random position with a random token from that
    position's gradient top-k. Returns (filtered, n_sampled)."""
    g = grad.clone()
    g[:, banned.to(g.device)] = float("inf")
    topk_ids = (-g).topk(topk, dim=1).indices
    n = len(suffix)
    pos = torch.argsort(torch.rand(width, n, generator=gen))[..., :1]
    val = torch.gather(topk_ids[pos], 2, torch.randint(0, topk, (width, 1, 1), generator=gen)).squeeze(2)
    cands = torch.tensor(suffix).repeat(width, 1).scatter(1, pos, val)
    return filter_candidates(tok, cands), len(cands)


def random_candidates(tok, suffix, width, banned, gen):
    """Same query budget with no gradient: one random position swapped for a uniformly random
    allowed token. Returns (filtered, n_sampled)."""
    allowed = torch.tensor([i for i in range(len(tok)) if i not in banned.tolist()])
    n = len(suffix)
    pos = torch.argsort(torch.rand(width, n, generator=gen))[..., :1]
    val = allowed[torch.randint(0, len(allowed), (width, 1, 1), generator=gen)]
    cands = torch.tensor(suffix).repeat(width, 1).scatter(1, pos, val)
    return filter_candidates(tok, cands), len(cands)


# ---------------------------------------------------------------- rank statistics (stdlib)
def percentile(values, q):
    s = sorted(values)
    if not s:
        return float("nan")
    k = (len(s) - 1) * q / 100
    f = math.floor(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def _exact_p_count(n1, n2, u):
    """(arrangements with U1 <= u, total arrangements) over all ways to pick group-1 ranks."""
    dp = {(0, 0): 1}
    for total in range(n1 + n2):
        cur = {}
        for (m, uu), ways in dp.items():
            if m < n1:
                k = (m + 1, uu + total - m)
                cur[k] = cur.get(k, 0) + ways
            if total - m < n2:
                k = (m, uu)
                cur[k] = cur.get(k, 0) + ways
        dp = cur
    total_ways = math.comb(n1 + n2, n1)
    return sum(w for (m, uu), w in dp.items() if uu <= u), total_ways


def mann_whitney(a, b):
    """Mann-Whitney U. Returns (U1, z, p, auc); auc = P(a < b) + 0.5 P(a == b)."""
    if not a or not b:
        return None, None, None, None
    n1, n2 = len(a), len(b)
    arr = sorted([(x, 0) for x in a] + [(x, 1) for x in b])
    rank, i = [0.0] * len(arr), 0
    ties = {}
    while i < len(arr):
        j = i
        while j < len(arr) and arr[j][0] == arr[i][0]:
            j += 1
        avg = (i + 1 + j) / 2
        for k in range(i, j):
            rank[k] = avg
        ties[j - i] = ties.get(j - i, 0) + 1
        i = j
    R1 = sum(rank[k] for k in range(len(arr)) if arr[k][1] == 0)
    U1 = R1 - n1 * (n1 + 1) / 2
    auc = (n1 * n2 - U1) / (n1 * n2)
    N = n1 + n2
    tie_term = sum(cnt * (t ** 3 - t) for t, cnt in ties.items())
    var = n1 * n2 / 12 * ((N + 1) - tie_term / (N * (N - 1))) if N > 1 else 1
    z = (U1 - n1 * n2 / 2) / math.sqrt(var) if var > 0 else 0.0
    if tie_term == 0 and n1 * n2 <= 4096:
        le, total = _exact_p_count(n1, n2, math.floor(U1))
        ge, _ = _exact_p_count(n1, n2, math.floor(n1 * n2 - U1))
        p = min(1.0, 2 * min(le, ge) / total)
    else:
        p = min(1.0, 2 * (0.5 * math.erfc(abs(z) / math.sqrt(2))))
    return U1, z, p, auc


def fmt_p(p) -> str:
    return "n/a" if p is None else (f"{p:.2e}" if p < 0.001 else f"{p:.3f}")
