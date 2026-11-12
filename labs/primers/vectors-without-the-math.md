# Vectors without the math

Labs that lean on this most: [LAB-25 · Vectors that are not words](../concept-embeddings/README.md), [LAB-40 · Similarity is not relevance](../arch-embedding/README.md), [LAB-27 · Anatomy and forensics of a transformer checkpoint](../arch-transformer/README.md) and [LAB-37 · Reading the hidden size off the logits](../attack-projection-theft/README.md).

Models store meaning as lists of numbers and compare them with a few simple operations. Every example on this page uses two or three numbers so you can check it by hand. Real models use hundreds or thousands, and the operations are the same.

## Single vectors

### Vector

A vector is a list of numbers, such as `[3, 4]`. You can picture it as an arrow from the origin to the point (3, 4).

### Dimension

The dimension is how many numbers the vector holds. `[3, 4]` has dimension 2. A small text embedding model outputs vectors of dimension 384, and the hidden size of a transformer (576 in SmolLM2-135M) is the dimension of the vectors it passes between layers.

### Norm

The norm is the length of the arrow: the square root of the sum of the squares. The norm of `[3, 4]` is `√(9 + 16) = 5`. Dividing a vector by its norm gives a unit vector of length 1 that points the same way: `[0.6, 0.8]`.

### Dot product

The dot product multiplies two vectors position by position and adds the results. `[1, 2] · [3, 4] = 1×3 + 2×4 = 11`. It is large when the vectors point the same way, 0 when they are at a right angle, and negative when they point apart.

### Cosine similarity

Cosine similarity is the dot product of two vectors divided by both norms. It measures only direction and ignores length. It runs from -1 (opposite) through 0 (unrelated) to 1 (same direction). For `[1, 0]` and `[1, 1]` it is `1 / (1 × 1.414) = 0.707`. `[1, 1]` and `[5, 5]` score exactly 1, because they point the same way.

### Distance and similarity

A distance is small when two vectors are close. A similarity is large when they are close. Euclidean distance is the norm of the difference: from `[1, 0]` to `[1, 1]` it is 1. For unit vectors the two carry the same information: `distance² = 2 - 2 × cosine`. Vector databases may report either one, so check which before you set a threshold.

### Embedding

An embedding is a vector a model produces for a token, a sentence or an image, trained so that similar inputs get nearby vectors. A search system embeds a query and returns the stored items with the highest cosine similarity to it. Nearby means "similar to this model", which is not always what you meant ([LAB-40](../arch-embedding/README.md)).

## Many vectors at once

### Matrix

A matrix is a table of numbers, such as a weight matrix of 576 rows by 576 columns. Multiplying a vector by a matrix produces a new vector, and every layer of a model does this.

### Rank

The rank of a matrix is how many independent patterns it contains. In `[[1, 2], [2, 4]]` the second row is twice the first, so there is only one pattern and the rank is 1. A `576 × 576` matrix can have rank up to 576. A [LoRA](ml-in-one-page.md#lora) update with `r = 4` has rank at most 4, however large the matrix.

### Subspace

A subspace is everything you can reach by scaling and adding a set of vectors. Those vectors span it, and its dimension is how many independent directions it has. In 3D, `[1, 0, 0]` and `[0, 1, 0]` span the flat floor where the third number is 0: a 2-dimensional subspace.

### SVD

SVD (singular value decomposition) rewrites any matrix as a list of rank-1 patterns, strongest first. Each pattern is a pair of directions and a strength. Adding the patterns back together gives the original matrix exactly, and keeping only the first few gives the best approximation of that rank.

### Singular values

The singular values are the strengths in that list. They are never negative and are sorted from largest to smallest. `[[3, 0], [0, 1]]` has singular values 3 and 1. `[[1, 2], [2, 4]]` has 5 and 0. The number of nonzero singular values is the rank, which is how LAB-27 tells a rank-4 LoRA edit from a full fine-tune, and how LAB-37 reads a model's hidden size off its outputs: the values drop to nearly zero after the hidden size.

### Projection

A projection keeps the part of a vector that lies in a direction or subspace and drops the rest. Projecting `[3, 4]` onto the horizontal axis gives `[3, 0]`. To project onto a unit vector `u`, take `(v · u) × u`. The projection is the closest point in that direction or subspace.

### Least squares

Least squares finds the parameters whose predictions miss the observations by the smallest total of squared errors. Example: fit `y = a × x` to the points (1, 2), (2, 4.2) and (3, 5.9). The best `a` is `Σxy / Σx² = 28.1 / 14 = 2.007`. LAB-37 uses a least-squares fit to check how closely the recovered weights match the true ones.
