# ML in one page

Labs that lean on this most: [LAB-50 · Gradients point both ways](../concept-gradients/README.md), [LAB-07 · What a 2 MB adapter changes](../adapt-lora/README.md), [LAB-08 · One gradient step](../attack-fgsm/README.md), [LAB-13 · Was this record in the training set?](../attack-membership/README.md), [LAB-16 · Poisoned demonstrations](../attack-sft-poison/README.md) and [LAB-33 · Teach a tiny model a new habit](../life-sft/README.md).

A model is a function with millions of adjustable numbers. Training adjusts those numbers until the function gives useful answers. This page names each piece in the order training uses it.

## What a model is

### Tensor

A tensor is a grid of numbers with a fixed shape. A list of 3 numbers has shape `[3]`, and a table of 576 rows by 576 columns has shape `[576, 576]`. Inputs, weights and outputs are all tensors.

### Weights and parameters

Weights are the numbers the model learns. Parameters means the same thing, and also covers biases (small numbers added after a multiplication). A layer that maps 576 inputs to 576 outputs holds `576 × 576 = 331,776` weights. A "135M model" has about 135 million of them.

### Layer

A layer is one step of the computation: it takes a tensor, does arithmetic with its weights, and passes the result on. A model is a stack of layers.

### ReLU

ReLU is the simplest activation function, a small rule applied to every number between layers: keep positive numbers and replace negative ones with 0. `ReLU([-2, 0.5, 3]) = [0, 0.5, 3]`. Without such a rule, a stack of layers could only compute straight-line functions.

### One-hot

A one-hot vector marks one choice out of many: all zeros except a single 1. With 5 classes, class 3 (counting from 0) is `[0, 0, 0, 1, 0]`. Labels are often written this way.

### Checkpoint and state dict

A state dict is PyTorch's map from each parameter's name to its tensor, for example `layers.0.self_attn.q_proj.weight -> [576, 576]`. A checkpoint is a file that stores it, sometimes with the optimizer's state too. A `.pt` or `.bin` checkpoint is a pickle, so loading it can run code ([LAB-01](../attack-unsafe-load/README.md)). A `.safetensors` checkpoint holds only tensors.

## From input to answer

### Forward pass

A forward pass runs one input through every layer and produces the output. Using a model to answer is called inference, and it is only forward passes.

### Logits

Logits are the raw scores the last layer outputs, one per possible answer. A digit classifier outputs 10 logits. A language model outputs one logit per token in its vocabulary. Logits can be any number, negative or positive, and only their differences matter.

### Softmax

Softmax turns logits into probabilities: raise `e` to each logit, then divide each result by their sum. Logits `[2, 1, 0]` become `[0.665, 0.245, 0.090]`, which add up to 1. Adding the same number to every logit changes nothing: `[12, 11, 10]` gives the same probabilities.

### Probability

A probability is a number from 0 to 1 that says how likely the model thinks each answer is. Many APIs return its logarithm (a logprob), which is always 0 or negative.

## How training works

### Loss and cross-entropy

The loss is one number that says how wrong the model was on an example. Lower is better. Classifiers and language models use cross-entropy: the negative logarithm of the probability the model gave the correct answer.

| Probability on the correct answer | Loss |
| :--- | :--- |
| 0.99 | 0.01 |
| 0.665 | 0.41 |
| 0.5 | 0.69 |
| 0.09 | 2.41 |

A model's loss on a record it trained on is usually lower than on a record it never saw. LAB-13 turns that gap into an attack.

### Perplexity

Perplexity turns a language model's average loss over a text into a number you can picture: `e` raised to the average loss per token. A perplexity of 4 means the model was, on average, as unsure as if it were picking between 4 equally likely tokens at each position. Lower means the text looked more familiar to the model. An average loss of 1.39 gives `e^1.39 ≈ 4`. [LAB-47](../life-data/README.md) uses it to filter training text, and [LAB-21](../attack-gcg/README.md) tests a perplexity filter as a defense, because an optimized suffix looks like gibberish to the model.

### Gradient

The gradient says, for every weight, how the loss changes if you nudge that weight up a little. A positive gradient means "increasing this weight increases the loss". The gradient can also be taken with respect to the input, which is how [LAB-08](../attack-fgsm/README.md) finds which pixels to change.

### Backpropagation

Backpropagation (backprop) is the algorithm that computes all the gradients in one backward sweep through the layers, from the loss back to the input. It costs about twice as much as a forward pass.

### Learning rate

The learning rate is the size of each update. It is a small number such as 0.001.

### Training step

A training step is forward pass, loss, backprop, update. The simplest update moves each weight against its gradient: `new weight = weight - learning rate × gradient`. With weight 0.5, gradient 2 and learning rate 0.01, the new weight is `0.5 - 0.01 × 2 = 0.48`.

### Batch

A batch is the group of examples processed together in one training step. Their losses are averaged, so one step learns from all of them at once. Batch size 8 means 8 examples per step.

### Epoch

An epoch is one full pass over the training set. With 1,000 examples and batch size 8, one epoch is 125 steps. Training for 4 epochs shows the model every example 4 times.

### Optimizer

The optimizer is the rule that turns gradients into weight updates.

- SGD (stochastic gradient descent) is the plain rule from the training step above.
- Adam keeps a running average of each weight's recent gradients and of their squares, and uses them to give every weight its own step size. It usually trains faster than SGD with less tuning.
- AdamW is Adam plus weight decay applied separately from the gradient: every step also shrinks each weight slightly toward 0. It is the usual default for transformers.

### Overfitting

Overfitting is when a model memorizes its training examples and stops generalizing. Its training loss keeps falling while its loss on held-out data stalls or rises. The gap between the two is what membership attacks exploit.

## Changing a trained model

### Fine-tuning

Fine-tuning is more training on a pretrained model, with a smaller dataset, to teach it a task or a habit. Supervised fine-tuning (SFT) uses example prompts paired with the replies you want.

### LoRA

LoRA (low-rank adaptation) freezes the original weight matrix `W` and trains two thin matrices `B` and `A` whose product is the update: `W + (alpha / r) · B · A`. The rank `r` sets how thin they are (and so how much the update can express), and `alpha` scales the update.

Example from LAB-07: for a `576 × 576` weight with `r = 4`, `B` is `576 × 4` and `A` is `4 × 576`. That is 4,608 trainable numbers in place of 331,776. With `alpha = 8` the update is multiplied by `8 / 4 = 2`. See [rank](vectors-without-the-math.md#rank) for what "low-rank" means.
