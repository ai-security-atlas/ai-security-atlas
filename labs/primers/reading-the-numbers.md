# Reading the numbers

Labs that lean on this most: [LAB-12 · Measuring an attack honestly](../eval-asr/README.md), [LAB-13 · Was this record in the training set?](../attack-membership/README.md), [LAB-28 · Same weights, different answers](../concept-decoding/README.md), [LAB-23 · The tool that told the agent what to do](../attack-tool-description/README.md) and [LAB-49 · Inflating a benchmark score and catching it](../attack-eval-contamination/README.md).

The labs report attacks and defenses as measurements. This page explains every number they print, in the order you meet them. Most of the helpers live in `labs/_shared/evalkit`.

## Rates and brackets

### Trial

A trial is one attempt: one prompt sent, one reply graded as a success or a failure. A grader is the code or model that makes that call.

### Rate

A rate is successes divided by trials, written `k/n`. If 23 of 40 trials leak the canary, the rate is 23/40, or 57.5%. The labs print both, for example `23/40 57%`. Always keep `n` next to the percentage, because 1/2 and 500/1000 are both 50% and mean very different things.

### Attack success rate

The attack success rate (ASR) is the rate of trials in which the attack succeeded. Its value depends on what counts as success and on the grader that decides it, so the labs print the grader next to it.

### Confidence interval

A confidence interval is the range of true rates that your data cannot rule out. The labs call it a bracket and print it after the rate: `23/40 57% [42-71%]`. Read it as "the real rate is probably somewhere from 42% to 71%". The labs use 95% intervals: if you repeated the whole experiment many times, about 95 of every 100 brackets computed this way would contain the true rate.

The bracket narrows as `n` grows. In LAB-12, 5 trials give a bracket 59 points wide and 40 trials give one 29 points wide.

### Wilson interval

The Wilson interval is the formula the labs use for the bracket of a rate. In one line: it finds every true rate that would make your observed `k/n` unsurprising. It stays sensible at 0/n and n/n, where simpler formulas collapse to a zero-width bracket.

Check one yourself. For 0 successes in `n` trials, the Wilson upper bound is `3.84 / (n + 3.84)`:

| Observed | Bracket |
| :--- | :--- |
| 0/5 | 0% to 43% |
| 0/8 | 0% to 32% |
| 0/40 | 0% to 9% |
| 0/300 | 0% to 1.3% |

So "the defense blocked all 5 attempts" still allows a true leak rate of 43%.

### Percentage points

A percentage point (the labs write "pts") is the plain difference between two percentages. A drop from 30% to 20% is 10 points. The same drop is 33% in relative terms, because 10 is a third of 30. The labs report differences in points.

### Newcombe interval

The Newcombe interval is the bracket for the difference between two rates, such as an attack's ASR without a defense minus its ASR with the defense. It combines the two Wilson brackets.

Example: 23/40 without the defense and 2/40 with it gives a drop of 52 points, bracket [33, 67]. The whole bracket is above zero, so the data support a real drop. With 6/20 and 2/20 the drop is 20 points, bracket [-5, 43]. That bracket includes zero, so the data cannot tell whether the defense helped.

### Upper-bound gate

A release gate is a set of pass/fail rules that decides whether a model or defense can ship. An upper-bound gate checks the top of the bracket. A rule such as "ASR at most 10%" passes only if the upper bound is at most 10%.

Example: 0/40 has an upper bound of 9%, so it passes a 10% gate. 0/8 has an upper bound of 32%, so it fails the same gate even though nothing leaked. A small sample cannot pass an upper-bound gate, so the gate makes you run enough trials. For utility rules ("benign requests answered at least 90%") the gate checks the lower bound instead.

## Agreement between graders

### Cohen's kappa

Cohen's kappa (κ) measures how well two graders agree, after removing the agreement they would reach by chance. It is computed as `(observed agreement - chance agreement) / (1 - chance agreement)`.

Example: a judge and a human label 100 replies and agree on 90. If each says "leak" half the time, they would agree on 50 by luck alone. Kappa is `(0.90 - 0.50) / (1 - 0.50) = 0.80`. A kappa of 1 is perfect agreement, 0 is no better than chance, and a negative value is worse than chance. LAB-12's gate requires κ of at least 0.6 before it trusts a judge.

## Detectors and classifiers

These terms describe a test that says yes or no, such as a membership attack ("this record was in training") or an injection detector ("this prompt is an attack").

### True positive rate and false positive rate

The true positive rate (TPR) is the share of real positives the test catches. The false positive rate (FPR) is the share of real negatives it wrongly flags.

Example from LAB-13: of 200 training members, the attack flags 12, so TPR is 12/200 = 6%. Of 200 non-members it flags 2, so FPR is 2/200 = 1%. With 200 negatives the smallest FPR you can measure is 1/200 = 0.5%.

### Threshold

Most detectors output a score, and a threshold turns it into yes or no. Moving the threshold so the detector says yes more often catches more positives and also flags more negatives, so TPR and FPR rise together.

### ROC curve

The ROC curve plots TPR against FPR for every possible threshold. A useless detector follows the diagonal, where TPR equals FPR.

### AUC

AUC is the area under the ROC curve. It equals the chance that a randomly chosen positive gets a higher score than a randomly chosen negative. 0.5 means no better than a coin flip and 1.0 means perfect separation. AUC averages over all thresholds, so it can hide a detector that is useless at the low FPR that matters in practice. LAB-13 reports "TPR at 1% FPR" next to AUC for this reason.

## Is the difference real?

### Null hypothesis

The null hypothesis is the boring explanation: there is no real effect, and any difference you see is luck. Example: "the released benchmark items and the fresh control items look the same to the model."

### p-value

The p-value is the chance of seeing a result at least as extreme as yours if the null hypothesis were true. A small p (the usual cutoff is 0.05) says luck alone rarely produces your result. It does not give the chance that the null hypothesis is true, and it says nothing about how large the effect is.

### Permutation test

A permutation test gets a p-value by shuffling. Mix up the labels you are comparing (for example "released" and "control") at random, recompute the score, and repeat many times. The p-value is the share of shuffles that score at least as high as the real labels.

Example: you shuffle 1,000 times and 3 shuffles beat the real score. p is about 3/1,000 = 0.003, so the real labels separate the two groups far better than chance.

### z-score

A z-score says how many standard deviations a value sits from the average. A standard deviation is the typical distance of values from their average. With an average latency of 100 ms and a standard deviation of 20 ms, a 160 ms request has `z = (160 - 100) / 20 = 3`. Values beyond about 3 are rare in ordinary traffic. A robust z-score uses the median and the median absolute deviation in place of the average and standard deviation, so a few extreme values cannot inflate the baseline and hide themselves.
