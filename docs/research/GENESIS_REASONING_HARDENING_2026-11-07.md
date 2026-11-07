# Genesis real-weight reasoning hardening — 2026-11-07

**Scope:** experimental, real pretrained Hugging Face weights, CPU inference; no Aurora Engine changes and no Kyro production deployment.

**Model:** `Qwen/Qwen2.5-0.5B-Instruct`, pinned to `c89bee90d9f811437d9735454613c35b4a3c4dc8`, weight SHA-256 `fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe`. This study **did not fine-tune** the checkpoint.

## Reproducible evaluation

- Test host: temporary `m7i-flex.large`, 2 vCPU / 8 GiB RAM, Amazon Linux 2023, ap-southeast-2.
- Weights read from the project's **encrypted private S3 store**, verified against the approved SHA-256 before inference. No public model-file upload to GitHub.
- Code: `tools/eval/hf_cpu_eval.py`, `tools/eval/score.py`, `tools/eval/genesis_hf_probe_v1.json`.
- Environment: CPU PyTorch 2.6.0; Transformers 4.51.3; deterministic greedy decoding; up to 80 generated tokens per raw call.
- Cases: **12 original, public, operator-authored smoke probes** (4 unit-price, 2 arithmetic, 2 small deduction, 1 geography, 1 source uncertainty, 1 exact-format instruction, 1 checksum explanation requiring human review). These cases were not used for training. They are **not** standardized, secret, unseen to developers after baseline, blinded, independently judged, or representative of general reasoning.
- Scoring: mechanical **pass**, **fail**, or **needs review**. Currency ambiguity triggers review; numeric responses use strict syntax; yes/no grading checks only initial conclusion; checksum explanation is automatically **review**. A mechanical pass is not a guarantee the entire explanation is coherent.

## Measured before/after on the SAME 12 prompts

| Configuration | Strict automatic passes | Automatic failures | Manual review |
|---|---:|---:|---:|
| Raw Qwen base weights | **4** | 6 | 2 |
| Genesis + Qwen, before fixes | **7** | 2 | 3 |
| Genesis + Qwen, after fixes | **10** | 1 | 1 |

This is a **within-suite regression comparison** with a small denominator. The fixes were targeted at observed failure classes, so do **not** infer a 10/12 score on unseen problems or a reliable general reasoning benchmark score.

## Implemented changes and observed cases

1. `genesis/unit_rate.py`: strict two-sentence cost-per-item parser, Decimal arithmetic, proof in answer, and refusal for discounts, shipping, taxes, item mismatch, and unclear rounding. All **four** new unit-price probes passed in Genesis while raw pretrained answers often produced incomplete reasoning and incorrect prices. The generator remains unchanged.
2. `genesis/arithmetic_routing.py`: narrowly validates elementary operators and numeric operands, translating natural-language math to the **existing** safe calculator; no Python evaluation of user strings. On the retest, `23 × 17` returned **391** via calculator, and `144 ÷ 12` returned **12.0**, both mathematically correct. Previously Genesis gave **489** on multiplication and an invalid-expression tool failure on division.
3. `genesis/epistemic.py`: exact time-stamped environmental/sensor values without a trusted data source do not receive speculative numbers from the local generator. Instead Genesis explicitly states the need for observation records. In the first pass the model fabricated **68% humidity** and falsely implied external-source support; after the gate it explicitly abstained. This is a narrow safeguard, not comprehensive hallucination detection.
4. `genesis/hf_backend.py`: when Qwen2 `use_sliding_window` is explicitly false, normalise the dormant `sliding_window` field to `None` **in memory only**, preventing Transformers 4.51.3 from interpreting it as enabled. No checkpoint/config file mutated. Explicit CPU attention mask remains. The captured test-host installation/evaluation log contained **zero** `Sliding Window Attention is enabled` warnings after this change. This removes the observed warning; it does **not** independently certify long-context numerical equivalence.

## Outstanding issues (promotion blocked)

- **Wrong factual answer:** Both the raw model and Genesis answered **Indian Ocean** when asked which ocean lies east of Australia; expected **Pacific Ocean**. This cannot be considered corrected by the arithmetic guardrails. Requires trusted retrieval, grounded factual evaluation or a better verified model, not special-casing the test answer.
- **Manual review:** The checksum explanation has not been independently graded. Statements about file integrity may sound convincing yet omit nuance or be inaccurate.
- The deduction grader accepts a correct leading yes/no even if subsequent reasoning is nonsensical. Raw Qwen gave a correct negative answer while adding an irrelevant invented biological explanation. **Pass-count overstates full-answer quality for those responses.**
- The unit-price and natural arithmetic parsers are **deliberately narrow**. They do not solve all reasoning or arithmetic tasks. Unsupported cases should fall back without manufacturing a verified proof.
- The epistemic gate covers exact, time-stamped environmental values; it does **not** prove that all other neural hallucinations are suppressed.
- No evidence of improved neural weights, AGI, calibrated factual reliability, hidden holdout generalisation, concurrent service capacity or public-beta readiness.

## CI / safety / operational details

- `tests/unit_rate_verification.py`, `tests/reasoning_guardrails.py`, `tests/hf_scoring.py` and `tests/question_routing.py` cover bounded routes, rejection cases and no automatic promotion of neural text to execution privileges.
- Both repository-wide GitHub Actions tests and neural adapter checks were green before the second real-weight run.
- EBS encrypted with deletion on termination, no inbound security-group rules, scoped S3 read/write IAM, SSM access, 35-minute boot-time shutdown and separate termination schedule. The instance is temporary; verify actual termination and remove temporary IAM/scheduler assets after report capture.
- Raw per-case outputs, timing, memory and grading stored under the project's **private S3** `genesis/hf/qwen2p5-0p5b-instruct/evaluation-v1/` prefix. The public repo does not include the bucket name.
- Active AWS Budgets alerts are **not a hard USD spending cap**; quote/verify final charges rather than stating a free run.

## Convergence gates

1. Independently grade the two manual-review responses and the remaining factual failure; inspect evidence against references.
2. Build a genuinely unseen, diverse set covering multistep reasoning, retrieval grounding, hallucinations, ambiguous math, privacy and prompt injection; withhold evaluation items from training and tuning.
3. Demonstrate production-safe observation/authorization separation under adversarial model outputs, then add Kyro's authenticated service integration and reliability measurements.
4. Only consider promoting the approved base model after those gates. The implementation stays on draft PR #33 until qualifying evidence exists.

The **Aurora = execution / Genesis = cognition / Kyro = interface** separation remains unchanged.
