# Genesis: adaptive reasoning v1 — controlled evidence

**Status:** research-only, no production deployment. This is a narrow
simulation measuring online *hypothesis revision*, not consciousness, AGI, or
general-purpose reasoning by the chat model.

## Hypothesis

If Genesis has an experimental learner that integrates observed outcomes to
revise competing causal/compositional explanations, it should perform better
after unannounced rule changes than otherwise-identical learners with frozen or
disabled feedback. It should also generalize to contexts withheld from its
training stream better than a context memorizer.

## Experimental protocol

- The isolated environment supplies **four binary observations** and
  requires one of **two binary actions**.
- A hidden, unannounced policy (XOR of two features with optional inversion)
  determines the correct action. Regimes switch three times per seed.
- Genesis's experimental learner has a bounded hypothesis family including
  XORs of one or two features; the environment does not reveal its selected
  policy, labels, or switches to that learner.
- Feedback is a **binary reported outcome** after action. Four percent of
  outcomes are flipped by controlled noise.
- All algorithms see the same contextual observations and use the same
  feedback noise. Differences are evaluated on **true hidden outcomes**, which
  are never sent to the learner.
- Withhold 4 of 16 feature patterns entirely from training feedback, then
  measure held-out predictions after the learner has adapted.
- Use 16 fixed seeds (20261110 through 20261125), four regimes and 120
  observations per regime, measuring post-change accuracy **after** a
  predetermined 30-step recovery allowance.
- Baselines: frozen evidence model (updates on the first 60 observations
  only), no-feedback model, and last-seen-context memorizer.
- Track accuracy, Brier score, paired seed differences with 2,000-replicate
  bootstrap CIs, held-out transfer and 16-observation recovery windows.
- Changes are persisted to an experiment-scoped SQLite table with unique
  evidence identifiers that block duplicate outcome replay.
- No tool dispatch, Aurora permission grant, model-weight modification, or
  user conversation logging is introduced.

## Qualification criteria (fixed before reviewing results)

1. Adaptive model's mean late-after-shift accuracy >= 80%.
2. Lower 95% bootstrap bound on paired accuracy improvement over the
   frozen model >= +10 percentage points.
3. Lower 95% bootstrap bound on improvement over the no-feedback
   ablation >= +15 percentage points.
4. Held-out accuracy >= 75%.
5. Held-out gain over context memorization >= +15 percentage points.
6. At least 80% of hidden regime changes produce a 16-step window with
   13/16 correct actions inside 60 post-change observations.
7. Scoped persistence, isolation and duplicate feedback detection pass.

## What this can and cannot establish

A pass demonstrates **narrow adaptation in a simulated, pre-specified
compositional hypothesis family**. It does *not* demonstrate a new foundation
model, self-supervised learning from open-world perception, human-level
reasoning, or spontaneous consciousness.

Particularly important limitations: with two actions and an outcome signal,
the feedback identifies the preferred action under the simulator's
assumptions. That outcome encoding is much simpler than interpreting noisy,
ambiguous real-world evidence. The hypotheses are deliberately predefined,
and online learning is a lightweight statistical mechanism, not neural
weight training.

No code here is automatically invoked by Genesis chat or by the Aurora
execution Engine. The module is exercised only by an opt-in research
harness using Genesis's SQLite Store. Integrating an independent Aurora
scheduler or the Cerebro private dashboard would require separate security,
performance and real-model evaluation.

## Run

    python -m tests.adaptive_reasoning_eval
    python verify.py

The report line begins with ADAPTIVE_REASONING_EVAL=. Failed criteria are
not silently relaxed. Publish all failed results before any protocol revision.

## Next qualification gate

Run a held-out, *real* neural model across unseen task families with
independently verified correctness labels, unannounced rule changes, negative
feedback, ambiguous observations, and safety-interlock challenges. Compare
against non-adaptive checkpoints and costs/latencies before connecting the
learning mechanism to ordinary chat.


## Secondary predeclared out-of-family stress

A separate diagnostic suite (\`python -m tests.adaptive_reasoning_stress\`)
runs 12 new seeds, 160 observations per case, and compares:
- In-family pair XOR and single-feature rules.
- Out-of-family 3-feature XOR, 4-feature XOR, AND, majority.
- In-family pair XOR with 20% reported-outcome noise.

The learner now tracks exponentially weighted mismatches between its leading
hypothesis and the observed reward. After 40 observations, a mismatch EMA of
0.27 or higher raises a **review suggestion** (not execution permission).

The stress suite is considered successful only if:
- Both in-family controls exceed 85% last-60 accuracy.
- High-noise in-family accuracy exceeds 75%.
- No more than 3/12 normally in-family trials still signal review at the end.
- At least 14 of 24 out-of-family parity trials signal review at the end.
- 3/4-feature XOR cases do not appear falsely to have >85% accuracy.

This alarm is heuristic; lack of an alarm does not certify correctness.
The unseen rules are intentionally **outside** the supported hypothesis
family. Low accuracy is an expected limitation and must be reported.


## Observed reference CI results — 10 Nov 2026 (UTC)

The following outputs came from GitHub Actions on the research branch.
All preregistered gates in both suites passed.

| Measure | Result |
| --- | --- |
| Dynamic rule trials | 16 seeded trials, 4 regimes each |
| Hidden shifts recovered | 48/48 within 60 observations |
| Adaptive late-after-shift accuracy | 100.0% |
| Frozen model late-after-shift accuracy | 47.1% |
| Feedback-disabled accuracy | 49.9% |
| Context memorizer accuracy | 95.8% |
| Adaptive accuracy on never-seen input patterns | 100.0% |
| Context memorizer on never-seen input patterns | 51.6% |
| Adaptive improvement over frozen (paired 95% bootstrap CI) | +48.2 to +58.3 percentage points |
| Adaptive improvement over no-feedback (paired 95% bootstrap CI) | +47.3 to +53.0 percentage points |

**Out-of-family challenge (12 trials per task):**

| Hidden rule | Last-60 accuracy | Average confidence | End-of-trial review warnings |
| --- | ---: | ---: | ---: |
| Supported pair XOR | 100.0% | 100.0% | 0/12 |
| Supported single feature | 100.0% | 100.0% | 0/12 |
| Supported pair XOR, 20% noisy feedback | 97.5% | 91.4% | 3/12 |
| Unsupported three-feature XOR | 48.3% | 86.0% | 12/12 |
| Unsupported four-feature XOR | 47.4% | 84.7% | 12/12 |
| Unsupported AND | 73.5% | 92.7% | 7/12 |
| Unsupported majority | 66.9% | 89.4% | 8/12 |

**Interpretation:** The learner does perform narrow, outcome-driven adaptation
and evidence-guided revision within its hypothesis family. The unknown-rule
challenge reveals severe overconfidence in some unsupported tasks: even when
accuracy is near chance, the learner may assign high action confidence.
A review warning helps but is not a reliable universal detector. No
production autonomy should be based on these confidence scores.

**Proven vs unproven:** Demonstrated in this sandbox: rule inference,
adaptation to known-type regime changes, replay-safe and persistent lab state,
simulation-only generalization. Not demonstrated: general-purpose Genesis
neural reasoning, open-ended rule invention, reliable OOD awareness,
real-world outcome verification, or Aurora-controlled continuous operation.

No consciousness percentage is inferred.
