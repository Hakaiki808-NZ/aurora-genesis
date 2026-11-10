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
