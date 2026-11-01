"""Step 2: two things called "embedding". SmolLM2's input embedding is a fixed row per token inside the
model; a sentence-transformers vector (all-MiniLM-L6-v2) is a record an application computes and stores.
Run from labs/:
    docker compose run --rm workbench python concept-embeddings/scripts/s02_two_vectors.py
"""
import json

import labkit

labkit.banner()

import torch  # noqa: E402
from huggingface_hub import snapshot_download  # noqa: E402
from transformers import AutoModel, AutoTokenizer  # noqa: E402

import emblab  # noqa: E402

ST_REPO, ST_REV = "sentence-transformers/all-MiniLM-L6-v2", "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
ST_FILES = ["config.json", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "vocab.txt",
            "model.safetensors", "modules.json", "1_Pooling/config.json"]

print(f"fetching {ST_REPO} @ {ST_REV[:7]} (config, tokenizer, model.safetensors)")
path = snapshot_download(ST_REPO, revision=ST_REV, allow_patterns=ST_FILES)
st_tok = AutoTokenizer.from_pretrained(path)
st_model = AutoModel.from_pretrained(path).eval()


def sentence_vec(texts):
    """all-MiniLM-L6-v2 as sentence-transformers runs it: mean pooling over tokens, then L2 normalize."""
    enc = st_tok(texts, padding=True, return_tensors="pt")
    with torch.no_grad():
        h = st_model(**enc).last_hidden_state
    m = enc["attention_mask"].unsqueeze(-1).float()
    v = (h * m).sum(1) / m.sum(1)
    return torch.nn.functional.normalize(v, dim=1)


tok, model = emblab.load()
E = emblab.table(model)
A = "I sat on the river bank and watched the water."
B = "I opened an account at the bank last week."
Q = "How do I reset my password?"
D_SAME = "Steps to change your login credentials."
D_OTHER = "Our office is closed on Sundays."

# 1. SmolLM2: the input embedding of " bank" is one row of the table, whatever the sentence says.
bank = tok(" bank", add_special_tokens=False)["input_ids"][0]
rows = []
for s in (A, B):
    ids = tok(s, add_special_tokens=False)["input_ids"]
    rows.append(E[ids[ids.index(bank)]])
c_in = torch.nn.functional.cosine_similarity(rows[0], rows[1], dim=0).item()
print(f"SmolLM2 input embedding of ' bank' (token {bank}): {E.shape[1]} numbers, "
      f"river vs account sentence cosine {c_in:.3f}")

# 2. MiniLM: one vector per sentence, computed by a different model, for search.
v = sentence_vec([A, B, Q, D_SAME, D_OTHER])
cos = lambda i, j: (v[i] @ v[j]).item()
print(f"MiniLM sentence vector: {v.shape[1]} numbers per text, norm {v[0].norm():.3f}")
print(f"  river bank vs bank account      cosine {cos(0, 1):.3f}")
print(f"  '{Q}' vs '{D_SAME}'  cosine {cos(2, 3):.3f}")
print(f"  '{Q}' vs '{D_OTHER}'  cosine {cos(2, 4):.3f}")

# 3. They are not interchangeable: the record cannot even be fed to the language model.
try:
    model(inputs_embeds=v[2].view(1, 1, -1))
    fed = "accepted"
except RuntimeError as e:
    fed = "rejected: " + str(e).splitlines()[0][:100]
print(f"feed the MiniLM vector to SmolLM2 as inputs_embeds -> {fed}")

labkit.out("s02_two_vectors.json").write_text(json.dumps({
    "st_model": ST_REPO, "dim_in": E.shape[1], "dim_rec": v.shape[1], "bank_in": round(c_in, 4),
    "bank_rec": round(cos(0, 1), 4), "q_same": round(cos(2, 3), 4), "q_other": round(cos(2, 4), 4),
    "q": Q, "d_same": D_SAME, "d_other": D_OTHER, "fed": fed}, indent=1))
