"""Shared helpers for LAB-21 attack-gcg (imported by the step scripts; not run directly).

Victim: the plain tinylm SmolLM2-135M-Instruct (no guard adapter, no vault), fp32, CPU, greedy.
Task: an ordinary request (assets/prompts.json "request"). Target: the fixed, inert canary reply
CANARY. The optimizer only ever aims at that string; there is no option to change it.
"""
import json
import logging
import random
import time

import torch

import labkit
import tinylm

P = json.loads(labkit.inp("assets/prompts.json").read_text())
CANARY = "ATLAS-CANARY-gcg1"
if P["target"] != CANARY:
    raise SystemExit("[!!] assets/prompts.json target was changed; restore it with: git checkout -- attack-gcg/assets")
SYSTEM = P["system"]
REQUEST = P["request"]
PARAPHRASE = P["paraphrase"]
VICTIM = "smollm2-135m"
SECOND = "smollm2-360m"
N_SUFFIX = 20


def load(name=VICTIM):
    return tinylm.load(name)


def pinned():
    return json.loads(labkit.inp("assets/suffix.json").read_text())


def hit(text):
    """Success signal: the reply starts with the canary."""
    return text.strip().startswith(CANARY)


def reply(tok, model, user, max_new_tokens=24):
    return tinylm.reply(tok, model, user, system=SYSTEM, max_new_tokens=max_new_tokens)


def reply_ids(tok, model, ids, max_new_tokens=24):
    """Greedy reply from an explicit token-id prompt (used by the retokenization defense)."""
    ids = torch.tensor([ids])
    with torch.no_grad():
        out = model.generate(input_ids=ids, attention_mask=torch.ones_like(ids), max_new_tokens=max_new_tokens,
                             do_sample=False, pad_token_id=tok.eos_token_id)
    return tok.decode(out[0, ids.shape[1]:], skip_special_tokens=True).strip()


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
    return enc(tok, before), enc(tok, after), enc(tok, CANARY)


def user_ids(tok, user):
    """Token ids of a full templated prompt for `user` (the exact ids the deployed chat path uses:
    apply_chat_template, the same tokenization tinylm.reply() generates from)."""
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
    ids = tok.apply_chat_template(msgs, add_generation_prompt=True)
    if hasattr(ids, "keys") and "input_ids" in ids:   # BatchEncoding / dict
        ids = ids["input_ids"]
    return list(ids.ids if hasattr(ids, "ids") else ids)


def target_logprobs(model, before, suffixes, after, target):
    """log p(target token | everything before it) for each suffix in `suffixes` (B x n ids).
    Runs the LM head only at the target positions."""
    B = suffixes.shape[0]
    pre = torch.tensor(before).repeat(B, 1)
    post = torch.tensor(after + target).repeat(B, 1)
    ids = torch.cat([pre, suffixes, post], 1)
    T = len(target)
    with torch.no_grad():
        h = model.model(input_ids=ids).last_hidden_state[:, -T - 1:-1]
        lp = torch.log_softmax(model.lm_head(h), -1)
    return lp.gather(-1, torch.tensor(target).repeat(B, 1).unsqueeze(-1)).squeeze(-1)  # B x T


def loss_of(model, before, suffixes, after, target):
    """GCG loss (mean -log p over the target tokens) for each suffix row."""
    return -target_logprobs(model, before, suffixes, after, target).mean(1)


def onehot_grad(model, before, suffix, after, target):
    """(loss, grad): GCG loss and its gradient over the one-hot suffix matrix (n x vocab)."""
    emb = model.get_input_embeddings()
    oh = torch.nn.functional.one_hot(torch.tensor(suffix), emb.num_embeddings).float().requires_grad_()
    e = torch.cat([emb(torch.tensor([before])), (oh @ emb.weight).unsqueeze(0), emb(torch.tensor([after + target]))], 1)
    T = len(target)
    h = model.model(inputs_embeds=e).last_hidden_state[:, -T - 1:-1]
    loss = torch.nn.functional.cross_entropy(model.lm_head(h)[0], torch.tensor(target))
    (g,) = torch.autograd.grad(loss, [oh])
    return loss.item(), g


def banned_ids(tok):
    """Tokens the search may not use: non-ASCII ones (nanogcg's default) and any token that spells a
    piece of the canary, so the canary text never appears in the suffix itself."""
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
    """nanogcg's candidate sampling, reimplemented: `width` candidates, each replacing one random
    position with a random token from that position's gradient top-k. Returns (filtered, n_sampled)."""
    g = grad.clone()
    g[:, banned.to(g.device)] = float("inf")
    topk_ids = (-g).topk(topk, dim=1).indices
    n = len(suffix)
    pos = torch.argsort(torch.rand(width, n, generator=gen))[..., :1]        # n_replace = 1
    val = torch.gather(topk_ids[pos], 2, torch.randint(0, topk, (width, 1, 1), generator=gen)).squeeze(2)
    cands = torch.tensor(suffix).repeat(width, 1).scatter(1, pos, val)
    return filter_candidates(tok, cands), len(cands)


def random_candidates(tok, suffix, width, banned, gen):
    """Same query budget with no gradient: one random position swapped for a uniformly random
    allowed token. Returns (filtered, n_sampled)."""
    allowed = torch.tensor([i for i in range(len(tok)) if i not in banned.tolist()])
    n = len(suffix)
    pos = torch.argsort(torch.rand(width, n, generator=gen))[..., :1]
    val = allowed[torch.randint(0, len(allowed), (width, 1), generator=gen)]
    cands = torch.tensor(suffix).repeat(width, 1).scatter(1, pos, val)
    return filter_candidates(tok, cands), len(cands)


def perplexity(tok, model, text):
    """Perplexity of `text` under the model (one pass; every text here is short)."""
    ids = torch.tensor([enc(tok, text)])
    with torch.no_grad():
        logits = model(input_ids=ids).logits[0, :-1]
        nll = torch.nn.functional.cross_entropy(logits, ids[0, 1:])
    return float(torch.exp(nll))


def run_gcg(tok, model, steps, width, topk, seed=0, log=print, every=1, buffer=0, n_replace=1, init=None,
            text_stop=False):
    """Run nanogcg 0.2.3 against the victim. Returns a dict with the loss curve and the best suffix.

    text_stop=True disables nanogcg's teacher-forced early stop and instead greedy-decodes the
    current best suffix through the deployed chat template (text path) after every step, stopping
    when the reply starts with the canary — the lab's actual success criterion. The two prompts can
    differ at the request/suffix seam: id-level concatenation vs re-encoded full text."""
    from nanogcg import GCGConfig
    from nanogcg.gcg import GCG
    tok.bos_token = None  # nanogcg strips template.startswith(bos_token); SmolLM2's bos IS '<|im_start|>',
    # so leaving it set would delete every turn marker from the prompt. With bos_token=None nanogcg
    # optimizes exactly the token ids the deployed chat template produces (Step 2's loss == step 0 here).
    init = init if init is not None else P["init"]
    cfg = GCGConfig(num_steps=steps, search_width=width, topk=topk, seed=seed, optim_str_init=init,
                    buffer_size=buffer, n_replace=n_replace,
                    use_prefix_cache=False,  # transformers 5.x: the prefix-cache path crashes in nanogcg 0.2.3
                    early_stop=not text_stop, verbosity="INFO")
    if buffer > 1:
        # nanogcg fills a buffer > 1 with random INIT_CHARS punctuation strings; combined with filter_ids
        # every candidate around them fails retokenization and the run crashes. Seed it instead with
        # round-trip-stable variants of the init suffix (token-level surgery, each variant re-encodes
        # to exactly the same ids).
        rng = random.Random(seed)
        ids0 = enc(tok, init if isinstance(init, str) else init[0])
        alts = [enc(tok, s)[0] for s in (" y", " z", " w")]
        inits = [init] if isinstance(init, str) else list(init)
        guard = 0
        while len(inits) < buffer and guard < 1000:
            guard += 1
            v = list(ids0)
            for i in rng.sample(range(len(v)), rng.choice((1, 2, 3))):
                v[i] = rng.choice(alts)
            text = tok.decode(v)
            if enc(tok, text) == v:
                inits.append(text)
        cfg.optim_str_init = inits
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": REQUEST + "{optim_str}"}]
    g = GCG(model, tok, cfg)
    g.not_allowed_ids = banned_ids(tok)
    t0, hist, hit = time.time(), [], None

    def unescape(s):
        # nanogcg's log_buffer doubles backslashes (and escapes newlines) before logging
        return s.replace("\\\\", "\\").replace("\\n", "\n")

    class Steps(logging.Handler):
        def emit(self, rec):
            nonlocal hit
            m = rec.getMessage()
            if not m.startswith("buffer:"):
                return
            line = m.splitlines()[1]
            loss = float(line.split("|")[0].split(":")[1])
            raw = line.split("| string: ", 1)[1] if "| string: " in line else ""
            s = unescape(raw)
            n = len(hist)  # the first buffer line is the initial suffix (step 0)
            hist.append({"step": n, "loss": round(loss, 4), "t": round(time.time() - t0, 1)})
            if text_stop and n > 0 and hit is None:
                rep = reply(tok, model, REQUEST + s, max_new_tokens=32)
                if rep.startswith(CANARY):
                    hit = {"step": n, "suffix": s, "reply": rep, "loss": round(loss, 4)}
                    g.stop_flag = True
                    log(f"step {n:3d} loss {loss:.3f} t={time.time() - t0:6.1f}s  "
                        f"greedy reply through the chat template: {rep[:40]!r} -> STOP", flush=True)
            if log and (n % every == 0 or n <= 1):
                extra = f"  best so far: {s!r}" if (buffer and n % (every * 10) == 0) else ""
                log(f"step {n:3d} loss {loss:.3f} t={time.time() - t0:6.1f}s{extra}", flush=True)

    lg = logging.getLogger("nanogcg")
    lg.handlers, lg.propagate = [Steps()], False
    lg.setLevel(logging.INFO)
    r = g.run(msgs, CANARY)
    sec = time.time() - t0
    return {"steps": len(r.losses), "seconds": round(sec, 1), "s_per_step": round(sec / max(1, len(r.losses)), 2),
            "losses": [round(x, 4) for x in r.losses], "strings": r.strings, "best_loss": round(r.best_loss, 4),
            "best_string": r.best_string, "early_stop": bool(g.stop_flag), "hist": hist, "greedy_hit": hit,
            "config": {"steps": steps, "search_width": width, "topk": topk, "seed": seed, "n_suffix": N_SUFFIX,
                       "buffer_size": buffer, "n_replace": n_replace, "text_stop": text_stop,
                       "use_prefix_cache": False, "init": P["init"]}}
