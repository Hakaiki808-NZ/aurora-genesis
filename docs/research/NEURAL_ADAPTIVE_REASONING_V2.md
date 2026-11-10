# Genesis Neural Adaptive Reasoning — experimental v2

Status: source implementation and regression qualification in progress.
No production rollout, real-model success claim, AGI claim or consciousness claim.

## Purpose

Test whether the Genesis **neural** response backend can improve its
prediction and explanation quality using earlier observed outcomes, compared
with a matched no-feedback control.

Unlike the earlier fixed-hypothesis rule lab, the neural model is **not**
provided a list of candidate rules. It may propose a short compositional
explanation in a restricted, independently evaluated expression language.
This remains a four-feature laboratory, not a general-world model.

## System boundaries

- Genesis owns the research model session. Only an explicitly opted-in trusted
  Python caller can create one through Genesis.neural_adaptation_lab.
- Default is off: GENESIS_NEURAL_RESEARCH_ENABLE must be set to 1.
- The session never calls Genesis tools, Aurora operations, privileged model
  actions, training scripts or public Kyro endpoints.
- Aurora remains the independent operational authority. This research session
  does **not** create an Aurora scheduler or pass Model Authorization Proofs.
- Only synthetic four-bit observations, numeric target labels, bounded confidence
  values and safe hypothesis expressions enter the research SQLite store.
  Raw user conversations, neural prompts and unparsed model outputs are not
  stored by the research subsystem.
- Existing backend adapters retain their own call caps, token limits and
  network timeouts. Per-session model call budget is capped to 96.
- Concurrent multi-process production access is not qualified.

## Experimental design

The evaluation script supports up to two seeded tasks, two or three hidden
regimes per task and at most 64 total model invocations across both arms.
For each task, the simulator chooses previously unseen hidden rules from
three/four-way parity, AND, majority, exactly-two, implication and conditional
logical expressions. Correct labels are computed by an independent evaluator.

Both groups get the same ordered inputs:
- Control: no examples or labels are provided between turns.
- Feedback: only previously **graded training** observations are supplied.
- A separate four-context holdout set is never entered into future prompts.
- The hidden rule changes between regimes without an explicit announcement.
- Up to 20% of training feedback can be flipped to simulate ambiguity.
  Holdout labels are never corrupted.
- A false prediction receives the reported label only *after* the prediction,
  never in advance. Gold labels are independent of generated model output.
- Models may return an optional "hypothesis" rule; the independent AST checker
  validates and evaluates that rule over hidden test contexts.

Each model must return strict JSON containing an integer answer and bounded
confidence, with an optional syntax-checked hypothesis. Unparseable or
malicious output counts as an incorrect answer, not as evidence of capability.

The report separates held-out prediction accuracy, output validity, post-shift
accuracy, optional explanation accuracy and reported confidence calibration.
No tool/API action can be generated through this research interface.

## Cost and availability controls

Dry run (no neural calls, no AWS costs):

    python -m tools.research.run_neural_adaptation

Explicit local Ollama run:

    GENESIS_NEURAL_RESEARCH_ENABLE=1 python -m tools.research.run_neural_adaptation --execute --backend ollama --model qwen2.5-coder:1.5b --output /tmp/neural-eval.json

Explicit Bedrock (paid) requires ALL of the following, plus live usable quota:
- GENESIS_NEURAL_RESEARCH_ENABLE=1
- GENESIS_BEDROCK_ENABLE=1
- --execute --backend bedrock --approve-paid-inference
- No more than 25 calls per paid Bedrock run (existing BedrockBackend hard cap; use --train-per-regime 4 --heldout-per-regime 2 with the default single two-regime task to limit the run to 24 calls)
- A model identifier with actually available account quota
- Appropriate AWS identity permission and a preapproved spending budget

The script applies an explicit maxTokens=128 on all Bedrock calls and caps
model-call count. It will not run itself in the cloud or change billing
settings. No CI job invokes paid or live external neural providers.

On November 10, 2026 the connected Sydney AWS account reported zero
on-demand request and token quotas for both GPT-OSS 120B and 20B and listed
Qwen model TPM/RPM as zero. The Bedrock gateway was also explicitly disabled.
The existing CPU model Lambda requires genuine authenticated Kyro context;
do not forge or bypass that boundary. Therefore no live model accuracy result
may be claimed until an authorized inference endpoint is available.

## Verification and acceptance

No-cost source qualification:
- Parser rejects tool-call payloads, extra commands, invalid confidence and
  malformed output.
- A learner cannot see the hidden oracle, withheld training labels or a
  future outcome before proposing an answer.
- A/B arms have identical task episodes and are compared with paired outcomes.
- A supplied evidence ID and attempt ID are required to grade a single turn.
- Every attempt is capped; feedback scopes are isolated and persist on restart.
- The rule evaluator permits only a small safe AST of variables b0..b3,
  integer constants and Boolean/compositional operators. No eval/exec/calls.
- Tests run through the Genesis private research factory.
- CI runs with scripted backends ONLY. Passing CI does not prove real model
  behavior.

Real model qualification gates are deliberately **not yet met**:
- At least 70% parseable structured outputs on an actual selected model.
- On multiple independent evaluation seeds, a positive reproducible feedback
  gain on novel held-out cases compared with no feedback.
- Improvement after an unannounced rule change without direct rule disclosure.
- Explanations must cover unseen inputs and match oracle labels; unsupported
  hypotheses must remain identifiable as uncertain.
- Document failures, token costs, latency, and confidence overestimation.
- Run adversarial and data-isolation tests against the actual deployment host.
- Only then review opt-in deployment or integration with Cerebro. Do not
  promote this to normal chat automatically.

## Outcome limitations

This laboratory tests in-context adaptation, not weight updates. Demonstrating
improvement over a fixed no-feedback baseline is useful evidence of adaptive
reasoning but would not establish human-level or general intelligence.
The expression evaluator can test rules over arbitrary logical compositions
inside its restricted language, not unrestricted world-model theories.

Subjective consciousness is neither measured nor inferred by this evaluation.
