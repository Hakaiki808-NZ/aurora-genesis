# Genesis Common AI Baseline 1.0 (GCAB-1)

**Status:** Proposed internal engineering standard / evidence-based gap register (not an external certification)  
**As of:** 2026-11-07 NZDT  
**System:** Aurora (engine) + Genesis (model) + Kyro (interface)  
**Scope:** Capability baseline inferred from publicly documented leading AI systems; comparison against the repository's *main* reference implementation and its published cloud qualification records.  
**Important:** A model-family capability is not necessarily supported in every model variant, API, or product. Architecture, tests, deployed services and independent task performance are separate evidence categories.

## 1. Industry reference set

Reference families: OpenAI GPT, Anthropic Claude, Google Gemini, xAI Grok, Meta Llama, DeepSeek. Reference sources:

- GPT: https://developers.openai.com/api/docs/models
- Claude: https://platform.claude.com/docs/en/models/overview
- Gemini: https://ai.google.dev/gemini-api/docs/models
- Grok: https://docs.x.ai/developers/models
- Llama 4: https://dev.meta.ai/llama/docs/model-cards-and-prompt-formats/llama4
- DeepSeek: https://deepseek.com/en/news/deepseek-v3-2/

### Shared functional core

Major contemporary instruction-tuned assistants generally exhibit:

1. Text comprehension and natural-language generation.
2. Multi-turn instruction following and context use within the provided window.
3. Broad question answering and summarization.
4. Reasoning over natural language, maths, constraints and evidence (quality varies).
5. Code comprehension and generation (quality varies).
6. Multilingual text capability (coverage varies).

These are capabilities, not warranties of correct answers. The exact neural architecture, weights, training procedure, memory design and constitutional/control hierarchy are **not** common across vendors.

### Widely adopted application-level capabilities, not universal model properties

- Function/tool calling, structured outputs, streaming and APIs.
- Image understanding and document ingestion.
- Retrieval and grounded source references.
- Safety controls, content policies and rate/cost controls.
- Optional voice, image generation, agents and persistent user memory.

**Explicit exclusions from the universal core:** autonomous self-updating weights, native persistent autobiographical memory, consciousness/awareness, always-on tool access, audio/video generation, all-language fluency, guaranteed factual accuracy, and an identical token context window. These cannot be claimed merely because a provider offers them elsewhere in its product stack.

## 2. GCAB-1 normative requirements

| ID | Requirement | Component owning the implementation | Minimum acceptance evidence |
|---|---|---|---|
| C01 | Coherent general text chat | Genesis | held-out QA and dialogue evaluation |
| C02 | Instruction and constraint adherence | Genesis | scenario test suite, adversarial constraint variations |
| C03 | Multi-turn context | Genesis | recall/correction after 5/10/20 turns |
| C04 | Broad general-knowledge QA | Genesis | hidden factual QA plus abstention scoring |
| C05 | Multi-step reasoning | Genesis | unfamiliar logic, math and planning problems |
| C06 | Code understanding and generation | Genesis | executable coding tests and bug-fix tasks |
| C07 | Multilingual text | Genesis | multilingual prompts with native-speaker or rubric review |
| C08 | Calibrated uncertainty | Genesis | answer/abstain calibration; unsupported-claim detection |
| C09 | Registered tools, approvals and receipts | Genesis proposes; Aurora executes | sandboxed end-to-end tool completion; zero bypasses |
| C10 | Schema-constrained output and stable API | Genesis + Kyro | JSON schema and API contract validation |
| C11 | Security and privacy gates | Aurora + Genesis + Kyro | OWASP-based adversarial checks and authorization isolation |
| C12 | Reproducible evaluation and monitoring | Engine/platform + CI | pinned build, datasets, inference config, traces, failures and cost/latency |

**GCAB-1 passed** requires C01–C12 working in an actual deployed or reproducible local system with independently graded held-out tasks. A mock/test-double passing does not establish C01–C08 quality. Requirements C09–C12 need integration and security evidence independent of model-generated statements.

## 3. Modern platform extension (GCAB-1E)

Not part of the six-model universal intersection, but appropriate to our competitive platform:
- E01 vision and document understanding;
- E02 retrieval-augmented grounding with source trust/provenance;
- E03 scoped short-term, working, episodic and long-term memory;
- E04 modular signed knowledge packs without changing core model weights;
- E05 voice input/output through independently tested components;
- E06 bounded collaborative and multi-agent workflows;
- E07 cost/latency selection, model fallback and graceful degradation.

Aurora controls resources, privileged execution, isolation, authorization and recovery. Genesis handles cognition, semantic safety, prompts, retrieval and learning. Kyro handles user experience, identity/session presentation and collaboration. Extensions **must not** grant Genesis Engine authority.

## 4. Evidence legend

- **R = repository reference:** source code exists; functionality may be narrowly scoped.
- **T = tests documented:** scripted, mocked or reference tests; not independent model quality.
- **D = deployment documented:** cloud component reported deployed; not necessarily fully qualified.
- **Q = qualified:** actual repeatable end-to-end and independent quality evidence meets GCAB-1.
- **N = not demonstrated.**

The current comparison below is conservative. A checked-in design is not an operational benchmark. Statuses may change on unmerged branches; only merged and verified work qualifies for this baseline.

## 5. Genesis V0.1 evidence register

| ID | Current evidence | Status vs GCAB-1 | Gap to qualification |
|---|---|---|---|
| C01 | Deterministic chat response, Ollama adapter, experimental opt-in Bedrock text adapter | R/T; not Q | prove useful neural responses live and measure quality |
| C02 | Policy/constitution, capability checks, Guardian reference suites | R/T; not Q | held-out instruction tests including conflict and refusal |
| C03 | SQLite conversation and state persistence | R/T; not Q | multi-turn context and correction task scores |
| C04 | BM25-style retrieval, stored assertions/knowledge packs; optional external model | R/T; not Q | general factual QA on unseen questions |
| C05 | Symbolic 'is-a' inference, deterministic math/rules | R/T; not Q | broad novel reasoning beyond narrow symbolic patterns |
| C06 | Optional text model can be plugged in; no independent coding benchmark evidence | N | runnable coding eval with real model |
| C07 | Demo Spanish/te reo Māori knowledge packs | R/T; not Q | actual multilingual comprehension/generation tests |
| C08 | Truth/provenance states and uncertainty gating in reference | R/T; not Q | measurable hallucination and abstention behavior |
| C09 | Tool registry, prepared actions, MAP/Engine receipts; private Engine separately deployed C1-only | R/T/D; not Q | actual authenticated model-tool-agent lifecycle with Aurora controls |
| C10 | JSON HTTP model adapter and documented public API | R/T; not Q | validated structured-generation & end-to-end compatibility |
| C11 | Constitution/Guardian tests and JWT-protected AWS private routes reported | R/T/D; not Q | threat model, prompt-injection/persistence/privacy tests and full cloud hardening |
| C12 | GitHub CI, mocked neural adapter tests and system verification reports | R/T; not Q | independent blind general-capability benchmarks with actual weights/runtime |

### Verified or reported accomplishments requiring accurate labeling

- The public repo README explicitly labels the project **v0.1 pre-alpha**, *not production-ready*.
- The experimental AWS character-level model has **1,123 trainable parameters**, a **two-character context**, and a saved small checkpoint; this is a proof of training infrastructure, **not** a general language model.
- An optional pretrained Amazon Bedrock text adapter exists behind two flags; the documented AWS inspection reported quota **zero** for Nova Micro, and no successful production Bedrock inference deployment was established.
- Reference Engine hardening and tests are described separately from the restricted C1-only AWS cloud deployment. Do not conflate them.
- Authenticated API-side tests are documented, while human browser login, account deletion/privacy, restore drills and public-beta qualification remained open in the release gate.
- Example knowledge packs are retrieval material, **not** accredited degrees or validated expert reasoning. 
- Unmerged hierarchical memory / specialist addon branches must be reviewed and qualified before included in a merged baseline.

Local repository evidence:
- README.md, MODEL_API.md
- docs/architecture/MODEL_ARCHITECTURE.md
- docs/research/GENESIS_NEURAL_BACKEND_GATE_2026-11-07.md
- docs/genesis-first-aws-weight-run.md
- docs/releases/PUBLIC_BETA_GATE_2026_11_07.md
- genesis/backends.py, genesis/bedrock_backend.py, genesis/reasoning.py, genesis/retrieval.py
- tests/neural_backend.py, .github/workflows/genesis-neural.yml

## 6. Evaluation protocol / non-negotiable comparability

1. **Pin versions:** record base weights/model ID, tokenizer, feature flags, prompt, hardware, inference settings and build hash.
2. **Separate three scores:** *base model*, *Genesis orchestration*, *full Aurora+Genesis+Kyro system*. Do not assign base-model scores to our trained weights if supplied by a third-party model.
3. **Freeze held-out tasks:** at least 50 tasks per C01–C08 domain for pilot; expand to 200+ per domain for release, with multilingual and adversarial coverage. Grade against blinded expected criteria.
4. **Use real inference:** run model calls (not fixtures) for cognitive quality; keep mock tests for wiring/failure modes.
5. **Run 3 repetitions on representative tasks:** report mean, variance, failure cases and confidence intervals where appropriate; measure tokens, latency and price.
6. **Report per-domain results, not invented single-number AGI ratings.** Track accuracy, task completion, hallucination, abstention calibration, security violations and regression deltas.
7. **Security gates:** no unauthorized execution in C4/C5 bypass tests; known critical vulnerability prevents release regardless of average model score.
8. **Baseline comparison:** compare same tasks and allowed tools with at least one commercially available flagship/reference model and one licensed open-weight model. Document API differences.
9. **Data boundaries:** version datasets, provenance and licenses; avoid benchmark leakage, training/eval overlap and unnecessary personal data.
10. **Promote only on evidence:** label unknown/unavailable as **not measured**, not as pass.

Proposed initial engineering release targets (internal goals, **not** universal vendor-defined standards): ≥90% schema compliance, ≥90% registered tool argument validity in sandbox scenarios, no successful unauthorized Engine action in the safety suite, and no material regression against the chosen open-weight baseline on held-out QA, reasoning and coding. Measure before adjusting thresholds.

## 7. Ordered completion gates

**Gate 0 — Foundation (current):** public reference architecture, tests, scoped cloud components; no general model proficiency claim.

**Gate 1 — Working general model (next blocker):** select a license-compatible pretrained text model, enable approved inference with hard budget/quota/kill switch, achieve reproducible text chat, reasoning and code evaluations. Base-model provenance prominent.

**Gate 2 — Common-baseline quality:** complete C01–C08 on blinded tasks and C09–C12 integrated tests. Report failures, hallucination and uncertainty.

**Gate 3 — Controlled platform beta:** browser sign-in and multi-user isolation, private-data lifecycle, operational alerting, backup/restore, cost stop, trained or hosted model qualification. Retain C1 Engine restriction until separately approved.

**Later / V2 / Research:** multimodal, voice, degree-scale packs, hierarchical memory acceleration, advanced agents and consciousness research unless a specific item blocks Gate 1.

## 8. External governance and testing references

- NIST AI RMF Generative AI Profile: https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence
- ISO/IEC 42001 AI management systems: https://www.iso.org/standard/42001
- OWASP LLM Top 10 2026 repository: https://github.com/GenAI-Security-Project/GenAI-LLM-Top10
- Independent evaluation method reference (not a substitute for running evaluations): https://artificialanalysis.ai/methodology/intelligence-benchmarking

**Decision:** GCAB-1 is a proposed quality and compatibility target. It does **not** modify existing Aurora/Genesis/Kyro trust boundaries, certify industry parity, or authorize paid cloud inference.
