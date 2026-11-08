# Neurol validation-regression control — 8 November 2026

## Problem and root cause

The 1,026,126-parameter Neurol GRU is trained on **40 short synthetic training
documents** (2,745 text bytes; **2,825 training tokens** after BOS/EOS). The
effective training-token/parameter ratio is **0.00275**, which is inadequate
evidence for general-purpose language competence. In the original research run,
training loss continued to fall but validation rose after step 200.

We tested interventions **on the validation split only** using the same
initialized weights, corpus, training-batch schedule and evaluation interval
(40 steps). The previously examined eight-document test split was **not** used
during hyperparameter selection.

## Controlled ablation (single initialization/seed)

| Regimen | Best validation loss | Best step | Final observed validation loss |
| --- | ---: | ---: | ---: |
| Original Adam, no dropout or scheduler | 1.8089 | 200 | 2.3731 (step 440) |
| AdamW (0.08 decay) + plateau scheduler | 1.8165 | 200 | 2.2582 (step 440) |
| Strong locked dropout (.12 input, .20 output) + AdamW (.08) + plateau | 1.8557 | 160 | 2.2237 (step 400) |
| **Mild locked dropout (.05 input, .10 output) + AdamW (.025) + plateau** | **1.7701** | **200** | 2.2418 (step 440) |

Mild regularization improved validation loss by approximately **2.14%** versus
the original baseline in this single-seed experiment. The higher dropout
settings were worse; strong regularization is **not** the default.

The plateau scheduler halves learning rate only when validation loss stalls.
It was added as a bounded option, not credited with improving the best
single-seed validation score independently.

## Safeguards implemented

The `ValidationGuard` shared by million-parameter GRU training and the
four-expert MoE pilot:

1. Preserves an exact in-memory copy of weights when validation improves.
2. Stops after two consecutive evaluations with validation loss more than
   5% above the best, or after the configured plateau patience.
3. Stops immediately on non-finite validation; does not overwrite a good
   checkpoint.
4. Restores the **best weights**, never the final deteriorated weights.
5. Maintains explicit research-only status and requires digest-pinned,
   opt-in backend activation.

For accelerated training, the mild locked dropout is applied *only* during
training. The saved GRU checkpoint remains exactly compatible with the
reference NumPy reset-before GRU inference equations and JSON-only format.

## Saved candidate: re-run with regression guard

With the selected setting, the guard stopped at **step 280** (versus
step 440 in the unconstrained comparison) and restored the step-200 model.

| Measurement | Result |
| --- | ---: |
| Parameters | 1,026,126 |
| Initial validation loss | 5.5530 |
| Best selected validation loss | 1.7701 |
| Best step | 200 |
| Actual stop | 280, validation_regression |
| Reused-test loss (exploratory only) | 1.5776 |
| Original baseline reused-test loss | **1.5490** |
| Unigram reused-test baseline | 3.0834 |
| Independent NumPy checkpoint validation | 1.7701214705 |
| Independent NumPy checkpoint test | 1.5775568062 |
| Trained checkpoint SHA-256 | `af50c2ffd6583c7a24b7888464e87aeac787daf510016706030a8228797dbd6e` |
| Cloud spend | $0 |

The independent reference confirmed finite weights, exact tensor sizes,
integrity digest, and full-context losses to within 0.0002.

**CRITICAL SELECTION CAVEAT:** Despite the mild improvement in repeatedly tuned
validation performance, the reused test loss is **worse** than the old GRU.
Keep the old GRU weights as the reference candidate; do **not** automatically
promote this regularized candidate. The reused test split is not a pristine
independent model-selection benchmark. Require a new licensed, larger, group
separated dataset with a genuinely untouched final evaluation split before
selecting a production checkpoint.

## Reproduction

Run the optional bounded trainer on the reviewed corpus with a pinned
initialized checkpoint digest (not the experimental candidate digest):

```bash
python -m pip install -r genesis/neurol/requirements.txt torch
python -m genesis.neurol.torch_train \
  --dataset examples/neurol/corpus.json \
  --initialized artifacts/neurol/million-untrained.json \
  --expected-sha256 <verified-initial-checkpoint-sha256> \
  --output artifacts/neurol/million-regularized.json \
  --report artifacts/neurol/million-regularized-report.json \
  --steps 600 --input-dropout 0.05 --output-dropout 0.10 \
  --weight-decay 0.025 --plateau-patience 2 \
  --max-validation-regression 0.05 --regression-patience 2
python -m tests.neurol_validation_guard
```

Optional experiments can disable dropout and weight decay with their
corresponding zero-valued CLI flags, but no option bypasses the pinned
initialized checkpoint or independent execution authority boundary.

## Next gate

Obtain a substantially larger, documented, permissioned and diverse corpus.
Reserve new group-disjoint validation and untouched test sets before training.
Use multiple seeds; compare a smaller dense model against the sparse MoE
pilot, and evaluate free-form generation quality, memorization, robustness and
real task performance—not cross entropy alone. No further steps on the
current 40-document dataset will establish conversational competence.
