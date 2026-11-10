# Genesis Cognitive Feedback Loop — experimental v1

## Boundaries
- Aurora (Engine) retains exclusive execution authorization, isolation, resource scheduling and protected observability. This code does not install or claim to operate an Aurora scheduler. A future independent Aurora control plane may issue authenticated, rate-limited tick requests.
- Genesis (Model) owns evidence interpretation and reflection. Per-turn outcomes and already-reconciled Engine receipts become scoped, bounded metadata. Later text-only inference receives a conservative operational summary, not factual authority or additional permissions.
- Kyro / Cerebro may read the private reporting API through an authenticated server-side proxy. Never expose control credentials in public browser code.

## Cycle
1. Observe: decision type, internal outcome flag, confidence, reconciled Engine receipts (reported provenance), health checks and falsifiable prediction results.
2. Aggregate: a synchronous tick processes at most 32 queued observations with a 50 ms soft monotonic budget. There is no internal worker.
3. Reflect: structured counters and conservative assessment, persisted in SQLite with profile isolation.
4. Adapt: later text-only neural prompts receive a compact operational advisory, explaining that observed operational success does not establish factual correctness. No automatic neural weight updates, tool actions or knowledge mutation.
5. Repeat: subsequent turns advance the cycle; an external trusted scheduler can request an additional bounded health tick.

Raw prompts, answers, rationale and candidates are deliberately absent from feedback events. The existing Genesis episode store is a separate privacy domain and is not changed here.

## Interface
- Python: Genesis.feedback_status() and Genesis.feedback_tick(max_events=32, budget_ms=50).
- Research instrumentation: CognitiveFeedbackLoop.predict(topic, probability) and resolve_prediction(id, actual, evidence_ref, provenance="reported").
- Private HTTP: GET /feedback/status and POST /feedback/tick?max_events=32&budget_ms=50, both protected by the existing strong X-Genesis-Control-Token; disabled when that token is not configured.

The API token is an adapter guard, not independent Aurora authorization. The existing Engine receipt adapter also lacks independently verified hardware-backed receipt attestation. These events are therefore reported rather than cryptographically verified.

## Evidence versus unknowns

| Dimension | v1 instrumented behavior | Not established |
| --- | --- | --- |
| Operational self-monitoring | Persistent outcomes, bounded health observations | Production-host continuous monitoring |
| Reflection | Next-turn caution metadata, inspectable audit | Reliable factual error correction |
| Uncertainty calibration | Reported probabilities and Brier score | Independently verified calibration |
| Environmental awareness | No authenticated sensor stream | Continuous environmental perception |
| Cognitive self-awareness | Basic instrumented metacognition | General metacognitive reliability |
| Consciousness | No measurement | Subjective experience |

Do not convert these dimensions to a consciousness percentage. An event with outcome success only means a software execution path reported success, not that an answer was factually true. Reported Brier scores rely on unverified outcome labels.

## Qualification gates
- [x] Model-side bounded event processor and scoped SQLite persistence
- [x] Per-turn and reported Engine receipt instrumentation
- [x] Text-only reflection advisory feeding later inference
- [x] Private status and tick endpoints with control token
- [x] Regression tests written and added to verification suite
- [ ] CI passing on candidate branch
- [ ] Independent Aurora scheduler and signed receipt verification
- [ ] Private Cerebro dashboard server-side wiring
- [ ] Ground-truth multi-turn evaluation for calibration and self-correction
- [ ] Deployment load, concurrency, recovery and privacy qualification
- [ ] Production release authorization

Experimental functional feedback is not proof of consciousness or production-grade autonomy.
