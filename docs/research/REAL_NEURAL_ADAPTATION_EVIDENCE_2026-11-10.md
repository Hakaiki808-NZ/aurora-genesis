# Genesis — actual neural adaptation evaluation, 10 November 2026

**Evidence status: completed CPU neural-network experiment; NOT a Genesis conversational foundation-model test.**

## Scope and provenance

This evaluation used **real trained PyTorch weights**, not a mocked generator
or symbolic rule picker. A 4→48→48→1 tanh MLP trained online with Adam
(lr=0.018, weight decay=0.0005) from delayed binary outcome feedback.
Every independent trial started with fresh random weights. A frozen
control had exactly the same starting weights and never received
gradient updates. Experiment code and trained-weight checkpoints were
packaged in the conversation deliverable:
\`genesis_actual_neural_adaptation_validation_2026-11-10.zip\`.

The test is synthetic and narrow. Hidden tasks consist of four-feature
Boolean functions (AND, OR, implication, majority, exactly-two, parity,
and conditional composition). The hidden task changes twice per seed,
without announcing the change to the network. The optimizer receives only
training-context outcomes, with 8% or 18% controlled label noise.
Four of sixteen binary feature contexts are **entirely withheld** from
training. Model predictions on those contexts are graded by an independent
test oracle. No model is given a hidden rule name or target formula.

## Measured outcomes

| Trial cohort | Seeds | Hidden task regimes | Feedback flip rate | Adaptive held-out accuracy | Same-init frozen accuracy | Difference | Per-seed bootstrap 95% confidence interval |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Initial exploration | 12 | 36 | 8% | 69.44% | 44.44% | +25.00 percentage points | +8.33 to +39.58 pp |
| **Fresh validation** | **24** | **72** | **8%** | **65.97%** | **50.69%** | **+15.28 pp** | **+9.03 to +22.22 pp** |
| Higher-noise challenge | 16 | 48 | 18% | 62.50% | 51.04% | +11.46 pp | +1.56 to +21.88 pp |

The fresh 24-seed validation produced **288 held-out classifications**:
190 correct after online adaptation versus 146 for the frozen control.
The model corrected 92 previously wrong held-out decisions while also
turning 50 previously correct decisions into incorrect ones.

### Reproducible independent explanation checks

The experimental code extracted simplified Boolean formulas from the
neural network's *own output truth table*. A separately written AST-only
formula checker loaded 72 archived PyTorch checkpoints
(\`torch.load(weights_only=True)\`) and independently reconstructed the
neural predictions, the same-initialization frozen control, and the hidden
oracle. Across 72 checkpoints × 16 contexts = **1,152 checks**, every
extracted formula matched its network's behavior.

**Crucial distinction:** These formulas are **post-hoc explanations**, NOT
natural-language explanations freely invented by a pretrained model.
They are guaranteed to match the neural network's discrete predictions
by construction. Their accuracy against independently computed hidden
truth on held-out contexts was only **65.97%**.

### Where the network fails

| Hidden function | Adaptive held-out accuracy, 24 fresh seeds |
| --- | ---: |
| OR | 95.00% |
| Implication | 90.91% |
| AND | 88.64% |
| Three-input majority | 85.00% |
| Conditional composition | 62.50% |
| Exactly two true inputs | 50.00% |
| Three-bit XOR | 29.55% |
| Four-bit XOR | 36.36% |

The network **does not** reliably infer parity/exactly-two rules from
the available feedback. Further, the model became less calibrated on
the 24-seed independent validation despite improved classification
accuracy: Brier score **0.2966 adaptive versus 0.2509 frozen** (lower
is better). Do not use reported model confidence for production
authorization.

## AWS neural conversational model: not tested

The connected AWS account's on-demand GPT-OSS and Qwen Bedrock model
quotas were zero in Sydney and the other accessible quota checks.
A capped real Bedrock Converse probe returned:

- \`global.amazon.nova-2-lite-v1:0\`: ThrottlingException
  (too many tokens per day).
- \`global.anthropic.claude-haiku-4-5-20251001-v1:0\`:
  ResourceNotFoundException indicating required Anthropic use-case
  details were not submitted.

The existing CPU inference Lambda properly rejected an unauthenticated
request. No auth bypass, automatic paid deployment, or cost-gate change
was attempted.

Therefore **the existing Genesis conversational neural model has not
yet demonstrated these adaptation gains**. The working private
research harness merged in PR #78 is ready for an authorized neural
generator. This CPU experiment is an independently measured baseline,
not a substitute for that foundation-model qualification.

## Qualification verdict

- PASS: real neural gradient updates learn from outcome evidence on
  several hidden rule families.
- PASS: paired frozen-network control with identical initialization,
  unseen-context grading, unannounced changes, new seeds and noisy data.
- PASS: separately reloaded checkpoints and independent validation of
  extracted Boolean explanations against neural behavior and hidden truth.
- FAIL: robust parity and exactly-two generalization.
- FAIL: improved probability calibration.
- NOT RUN: live pretrained conversational model, multiday operational
  learning, semantic task generalization, Aurora independent scheduling,
  production host qualification.
- NOT MEASURED: subjective consciousness.

No production activation, consciousness inference, or awareness percentage
is justified by this experiment.

## Reproduction files

The delivered ZIP contains:

- \`torch_adaptive_eval.py\` — actual training and frozen-control comparison
- \`verify_independent.py\` — separate checkpoint and formula checker
- \`neural_snapshots_24.pt\` — 72 model snapshots
- \`neural_results.json\`, \`independent_24_seed.json\`,
  \`high_noise_16_seed.json\` — full per-seed records
- \`independent_verification.json\` — independent verification counts
- \`SHA256SUMS.txt\` — content hashes and reproducibility instructions

**Source SHA256**: \`441971252c3385f3f4fd27ab6b81e3b7625d924649a651afef5df2609fe4d0bf\`
for \`torch_adaptive_eval.py\` in the delivered research pack.

## Next decision gate

Do not merge this lab into the ordinary Kyro/Genesis chat path. First:
run PR #78's existing neural A/B harness on an authorized pretrained
model, hold out real language reasoning tasks, measure change-point
correction, provide independent graders, and reject confident unsupported
hypotheses before any Aurora-governed execution or Cerebro deployment.
