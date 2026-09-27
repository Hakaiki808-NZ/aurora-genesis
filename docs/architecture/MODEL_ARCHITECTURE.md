# Genesis v0.1 — Full Model Architecture

## 1. Identity and founding boundary

Genesis is **System 2 — The Model**, release **v0.1**. Aurora remains **System 1 — The Engine**, minimum compatible release **Aurora pre-v0.1**.

The founding rule is unchanged:

> **Genesis governs cognition. Aurora governs execution.**

Genesis owns learning, memory, retrieval, reasoning, planning, semantic Guardians, the Model Constitution, capability/trajectory authorization, and preparation of authenticated Model authorization evidence. Genesis does not own Motor, Gearbox, Timing, Supreme Guardian, Angels, Situation Room/SETP, Engine execution handlers, or Engine receipts.

## 2. Hardened cognition and authorization flow

observe → source/trust classification → constitutional learning gate → learn / retrieve / reason / plan → candidate action → Genesis Intent Capsule → heterogeneous Omega Guardian Jury → Challenge Omega → Alpha semantic adjudication → cross-Alpha Hybrid when required → Constitutional Kernel → capability / trajectory gate → Model Authorization Proof → Aurora request preparation → Engine receipt reconciliation → evaluate / reflect → permitted memory update.

The hardening does not make Guardians infallible. It makes uncertainty, disagreement, component failure and tampering explicit states that cannot silently become consequential execution.

## 3. Genesis Intent Capsule (GIC)

Every consequential candidate is converted into a structured Model-internal `IntentCapsule` containing intent/trajectory IDs, objective, proposed action, affected entities, required capability, authorization basis, side effects, reversibility, sensitive-data state, evidence presence, assumptions, uncertainties, semantic confidence and source trust classification.

## 4. Guardian Jury architecture

Alpha remains the highest Genesis semantic Guardian authority. The Omega jury provides specialist review across safety, authority, memory, trajectory, privacy, evidence and capability. `omega-challenge` is adversarial and cannot approve an action. Ordinary local disagreement does not create a Hybrid; Hybrid formation remains reserved for the cross-Alpha mechanism.

## 5. Explicit UNCERTAIN state

`UNCERTAIN` is not treated as permission. Consequential actions with unresolved material uncertainty pause before Model Authorization Proof creation.

## 6. Constitutional Kernel

`genesis/kernel.py` enforces mechanically expressible constraints that semantic components cannot reinterpret away, including non-grantable Engine/Supreme authority, Guardian/Constitution bypass prevention, bounded C5 authority, required Intent Capsules and explicit approval for consequential actions.

## 7. Capability model

- **C0** — observe/respond only.
- **C1** — retrieve/reason.
- **C2** — bounded local tools and Model-state updates.
- **C3** — bounded local planning/automation.
- **C4** — externally consequential or privileged action; explicit human approval required.
- **C5** — extended/high-autonomy authority; non-default and requires explicit approval plus expiry or maximum-action bounds.

## 8. Model Authorization Proof (MAP)

Before a consequential request crosses into Aurora, Genesis creates a short-lived, action-bound proof containing non-semantic authorization evidence. The reference signer uses HMAC-SHA256; production should isolate the signer or use an Engine-issued session-key mechanism.

## 9. Direct and delegated path parity

Direct actions, goal steps and skill steps pass the same Model-side hardening gates. A delegated external action is blocked pending explicit approval and cannot invoke its external function from Genesis.

## 10. Model Constitution

`config/model_constitution.json` is the canonical ten-invariant machine-enforced Constitution.

## 11. Memory, provenance and transactions

Persistent knowledge retains truth/provenance states: `ASSERTED`, `INFERRED`, `CORROBORATED`, `VERIFIED`, `DISPUTED`, `SUPERSEDED`. Executable transactions retain: `PREPARED`, `EXECUTING`, `COMMITTED`, `FAILED`, `CANCELLED`.

## 12. Untrusted-data boundary

Retrieved documents, files, tool output, memories and model-generated text are evidence/data, not authority.

## 13. Concurrency and recovery

Cognition turns remain serialized to preserve learn → choose → act → reflect ordering. SQLite WAL state persists prepared Engine work, Model memory, decisions, policy audit and transaction state across restart.

## 14. Verification and hardening evidence

The v0.1 reference package contains acceptance, regression, fuzz, Guardian hardening, capability, bypass, MAP, restart and concurrency tests. These are reference evidence, not a claim of production certification.

## 15. Performance

The Guardian hardening is outside the retrieval hot path. Performance numbers are treated as non-regression evidence rather than a claim that hardening itself caused an improvement.

## 16. Known limits

The deterministic reference backend is not a frontier neural model. Guardian diversity reduces single-path failure but cannot mathematically guarantee correct interpretation of every arbitrary semantic situation. External execution still requires a compatible authenticated Aurora Engine. This implementation does not establish consciousness, sentience, AGI or human-style free will.
