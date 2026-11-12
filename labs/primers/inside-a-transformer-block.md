# Inside a transformer block

Labs that lean on this most: [LAB-27 · Anatomy and forensics of a transformer checkpoint](../arch-transformer/README.md), [LAB-26 · Who attends to whom](../concept-attention/README.md), [LAB-38 · The cache remembers](../concept-kv-cache/README.md), [LAB-44 · Reading and writing the residual stream](../concept-residual/README.md) and [LAB-34 · The guardrail is a model too](../arch-encoder/README.md).

A transformer turns a list of tokens into one vector per token, passes those vectors through a stack of identical blocks, and reads the next-token [logits](ml-in-one-page.md#logits) off the last one. The numbers on this page come from SmolLM2-135M, the small model several labs use: 30 blocks, vectors of 576 numbers, a vocabulary of 49,152 tokens.

## Getting text in

### Token

A token is a piece of text, often a word or part of a word, with an integer id. The tokenizer splits your text into tokens before the model sees anything. `" hello"` with its leading space is one token. A rare word can be several.

### Token embedding

The token embedding is a lookup table with one row per token id. Each row is a [vector](vectors-without-the-math.md#vector) of the model's hidden size. SmolLM2-135M's table is `49,152 × 576`, about 28.3 million numbers. Looking up a token's row is the first thing the model does.

### Hidden size

The hidden size is the length of the vector that represents each token inside the model: 576 for SmolLM2-135M, 4,096 for many 7B models.

### Position and RoPE

Attention by itself does not know the order of tokens, so the model needs position information. RoPE (rotary position embedding) rotates each query and key vector by an angle that grows with the token's position, so the attention score between two tokens depends on how far apart they are.

## One block

Each block has two parts, attention and an MLP, and each part reads the residual stream and adds its result back into it.

### Residual stream

The residual stream is the running vector for each token that flows through all the blocks. Every part reads it, computes something, and adds its output to it: `x = x + attention(norm(x))`, then `x = x + mlp(norm(x))`. Nothing overwrites it, so information written by an early block is still there for later ones. That is why [LAB-44](../concept-residual/README.md) can read and steer it.

### RMSNorm

Normalization rescales a vector to a standard size before a part reads it, which keeps the numbers stable across 30 blocks. RMSNorm divides the vector by its root-mean-square (the square root of the average of its squared values), then multiplies each position by a learned scale. For `[3, 4]` the root-mean-square is `√((9 + 16) / 2) = 3.54`, so the vector becomes `[0.85, 1.13]` before the scale.

### Attention

Attention lets each token gather information from the tokens before it. Every token computes three vectors from its residual stream:

- The query says what this token is looking for.
- The key says what this token offers, for other tokens' queries to match against.
- The value is the content this token passes on when it is matched.

The score between two tokens is the [dot product](vectors-without-the-math.md#dot-product) of one token's query and the other's key, divided by the square root of the head size. [Softmax](ml-in-one-page.md#softmax) over all earlier tokens turns the scores into weights, and the output is the weighted sum of their values. These weights are what "who attends to whom" in [LAB-26](../concept-attention/README.md) shows.

### Heads

A head is one attention computation. A block runs several in parallel, each on its own slice of the vector, so each head can track a different relation. SmolLM2-135M has 9 query heads of size 64 (the `head_dim`): `9 × 64 = 576`. The heads' outputs are joined and mixed by one more matrix (`o_proj`).

### GQA

GQA (grouped-query attention) lets several query heads share one key head and one value head. SmolLM2-135M has 9 query heads and 3 key/value heads, so each key/value head serves 3 query heads. That makes the key and value projections 192 wide (`3 × 64`) and the KV cache 3 times smaller.

### MLP

The MLP (multilayer perceptron, also called the feed-forward layer) works on each token separately. It widens the vector, applies a nonlinear function, and narrows it back. In SmolLM2-135M it goes from 576 to 1,536 and back to 576, using three matrices: `down(silu(gate(x)) × up(x))`. Most of a model's parameters sit in the MLPs.

### Output head

After the last block, a final norm and one more matrix (the output head, or `lm_head`) turn each token's vector into one logit per vocabulary token. Some models, including SmolLM2-135M, reuse the token embedding table for this.

## Running it

### KV cache

When the model writes a reply, every new token needs the keys and values of all earlier tokens. The KV cache stores them so they are computed once. Its size per token is `layers × 2 × key/value heads × head_dim × bytes per number`. For SmolLM2-135M in 32-bit floats that is `30 × 2 × 3 × 64 × 4 = 46,080` bytes per token. A server that shares a cached prefix between users can leak timing ([LAB-24](../attack-cache-sidechannel/README.md)).

### Prefill and decode

Prefill is the first pass over the whole prompt. It processes all prompt tokens in parallel and fills the KV cache, so a long prompt mostly costs time before the first token appears. Decode then generates the reply one token per pass, each pass reading the cache. When a server finds a prompt prefix already in its cache, it skips that part of the prefill.

### Encoder and decoder

A decoder lets each token attend only to the tokens before it (a causal mask), so it can write text left to right. Chat models such as SmolLM2, Qwen and Llama are decoders. An encoder lets every token attend to every other token in both directions and outputs vectors that describe the whole input. Encoders such as BERT are used for classifiers, guardrail detectors and [embeddings](vectors-without-the-math.md#embedding). Some models, such as T5, have both: an encoder reads the input and a decoder writes the output.
