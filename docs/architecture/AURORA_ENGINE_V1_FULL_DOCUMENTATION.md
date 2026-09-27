# AURORA v0.1 — Complete Engine Documentation

**System:** The Engine  
**Release name:** AURORA  
**Major generation:** v0.1  
**Canonical release:** v0.1  
**Reference build:** 8  
**Status:** Hardened runnable reference baseline; target-specific production assurance remains deployment work.

## 1. Purpose and identity

AURORA is the execution/runtime system. It supplies the deterministic, resource-managed, auditable boundary in which a compatible Model operates. AURORA governs execution rather than task meaning.

## 2. Founding separation

**Genesis governs cognition. Aurora governs execution.**

Supreme does not choose Model semantics. Alphas cannot grant Engine authority. Angels are Engine-owned sensors/interlocks, not Guardians.

## 3. v0.1 invariants

1. Engine authority and Model semantic authority remain separate.
2. Only Engine-hosted Motor handlers perform admitted side effects.
3. A workload cannot grant itself Engine/Supreme authority.
4. Supreme authority is finite, operational and Engine-only.
5. No public `SUPREME.*`, `ANGEL.*` or protected-observability control endpoint exists.
6. Gearbox owns allocation; Timing owns synchronization/regulation.
7. Engine/Angel resource safety floors are non-allocatable to workloads.
8. Situation Room / SETP reject task semantics and reasoning.
9. Stale session epochs are rejected.
10. Realignment requires Engine-originating verification and cannot be self-certified by Model Guardians.
11. Replay, reordering, identity mismatch and release rollback fail closed.
12. Incompatible Engine contract changes require a successor Engine generation/name.

## 4. Engine states

Legal states: `OFF`, `BOOTSTRAP`, `VERIFYING`, `READY`, `RUNNING`, `DEGRADED`, `RESTRICTED`, `SAFE_HOLD`, `MAINTENANCE`, `SHUTDOWN`.

Normal startup: `OFF -> BOOTSTRAP -> VERIFYING -> READY -> RUNNING`.

## 5. Sessions, epochs and cleanup

Every Model session receives a UUID and monotonically increasing Engine epoch. Requests carrying a stale epoch are rejected. Session close terminates Angel Cells, invalidates MAP state, releases Gearbox allocation, removes Engine grants, clears protected session signals and removes cached request receipts.

## 6. Workload Capability Manifest

A manifest declares workload ID, minimum Aurora release, requested capability names, resource domains and minimum resource units. It is validated against the running Engine generation/update and safe allocatable capacity. A manifest never grants Motor execution authority.

## 7. Motor

Motor is the only Engine execution drive. It owns handlers, rejects protected `SUPREME.*`/`ANGEL.*` handler registration, dispatches after the Engine admission chain and produces authoritative receipts.

## 8. Gearbox / Gears / 4WD

Gearbox owns resource allocation across CPU, RAM, GPU/accelerator and I/O. Engine/Angel safety floor is never allocatable.

## 9. Timing

Timing records and regulates hand-off timing, spacing and jitter. Timing exposes no allocation authority and cannot inspect task semantics.

## 10. Engine Contract v0.1

Public endpoints include identity, capabilities, health, timing, session lifecycle, resource minimums, execution requests, Situation Room/SETP, and Alpha Beacon. No public Supreme, Angel-management or Protected Observability endpoint exists.

## 11. Situation Room / SETP

Situation Room is a priority operational incident queue. SETP uses Engine-signed, short-lived, one-use tickets bound to Engine instance, Model session, source identity and nonce. Replay, expiry, ticket mutation and semantic/free-form fields are rejected.

## 12. Alpha Beacon

Alpha Beacon is one-way sanitized Model-to-Engine operational telemetry. Semantic Model reasoning is rejected.

## 13. Supreme Guardian

Supreme is internal to Aurora and limited to finite operational actions. It has no Model-facing endpoint and no authority to choose or rewrite Model semantics.

## 14. Realignment

Expected Alpha identities advance monotonically through `NOTIFIED -> INVESTIGATING -> CORRECTING -> VERIFYING`. Timeout is audited and fails closed to `SAFE_HOLD`.

## 15. Angel Inspection Plane

Angels execute outside the Genesis process in separate OS processes. Stronger deployment isolation can be layered beneath the same contract.

## 16. Protected Observability Fabric

Aurora owns the observation channel. Engine admission and Angel verdict events are captured inside Aurora before Motor dispatch. Semantic fields are rejected by schema. Events are hash chained.

## 17. Angel attestation

The Angel worker image SHA-256 is release-pinned. Angels establish ephemeral identity and Aurora verifies identity/session/code-hash/challenge metadata before issuing an Engine-signed certificate.

## 18. Angel Interlock Tokens

Tokens bind Angel type, session, request ID, action digest, verdict, reason, timestamp/expiry, nonce and monotonic sequence. Aurora validates signature, binding, expiry and one-use state before Motor admission.

## 19. Model Authorization Proofs

For critical/high-consequence execution, Aurora independently validates a short-lived Model Authorization Proof for schema, Model release, Constitution hash, capability, verdicts, action digest, TTL, nonce, signature and replay state.

## 20. Dual authorization

External execution requires both Model semantic/capability authorization and independent Aurora Engine grant.

## 21. Selective fail-closed

Required-Angel loss and any available Angel `BLOCK` or `REALIGN_REQUIRED` condition can degrade, restrict or block execution depending on tier.

## 22. Engine identity and hardware trust

The Engine exposes its public-key fingerprint and supports stronger hardware-backed keying where target hardware permits. No unsupported physical-hardware assurance claim is made by the reference build.

## 23. Service supervision and update control

Service Supervisor tracks health and restart counts. Update verification rejects invalid signature/hash status and release rollback.

## 24. Audit

Engine audit entries and Protected Observability are hash chained.

## 25. Verification evidence

The reference package includes regression, hardening, adversarial, cross-system and Model verification material. These results are reference evidence, not production certification.

## 26. Production assurance boundary

Reference implementation does not equal production certification. Remaining target-specific work includes mandatory access-control policy, optional microVM/TEE Angel backends, physical TPM/HSM/TEE qualification, measured boot/remote attestation, durable crash-safe persistence, real cgroup/GPU/I/O enforcement, signed reproducible release pipeline, kernel/covert-channel review, independent penetration testing and formal verification where justified.

## 27. Release statement

v0.1 is the first public development baseline and preserves the founding Model/Engine authority separation.
