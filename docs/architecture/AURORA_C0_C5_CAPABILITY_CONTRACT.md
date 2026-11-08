# Aurora capability tiers C0–C5 — implementation contract v0.1

**Status:** C0/C1 are reference-policy tiers; AWS private alpha remains **C1-only**.
C2–C5 are **offline conformance simulations**, not live Engine execution.
**Release gate: HOLD.** This contract does not promote production capabilities.

## Authority boundary

Genesis may *propose* a tier after its Guardians, Constitutional Kernel and
policy have approved an intent. That output is not an Aurora grant. Aurora must
derive the minimum tier from an Engine-owned, versioned operation catalogue;
Model-supplied capability labels can only increase, never decrease, its risk
classification. Kyro authenticates the user and gathers consent/approval but
cannot mint Engine authority. Supreme, Angel administration, and Engine policy
control are non-grantable to Genesis at all levels.

## Level-by-level specification

| Tier | Reference operation | Admission requirements | Live status |
| --- | --- | --- | --- |
| C0 | `reason` | Valid session, Genesis semantic authorization; no effects | Policy only |
| C1 | `restricted_read` | C0 + independently verified Engine grant and bounded isolated worker | Restricted cloud alpha; host adapter conformance only |
| C2 | `reversible_local_write` | C1 + scoped grant, rollback plan, least-privilege local containment | Simulation only |
| C3 | `scoped_external_update` | C2 + idempotency and external scope binding | Simulation only |
| C4 | `privileged_change` | Independent proof verification, hardware-backed Angel verification, trusted human approval, operator unlock, scoped Engine grant | Simulation only |
| C5 | `autonomous_workflow` | C4 + **both** bounded expiry and per-workflow action quota; durable revocation and cancellation | Simulation only |

**Conservative Genesis compatibility:** Genesis currently classifies *all*
external side effects as C4, even if an Aurora operation catalogue might
eventually classify a proven reversible external update as C3. This is an
intentional stricter Model-side default.

## Code in this branch

- `tools/aurora_c_levels.py`: non-executing admission simulator, fixed Engine
  operation classification, default-deny, session/epoch/scope-bound *test*
  grants, revocation, quotas, replay rejection, and hash-chained operational
  audit samples. Evidence flags in the simulator are **not verified security
  evidence**; private Aurora must produce those attestations itself.
- `tests/test_aurora_c_levels.py`: negative and positive simulation tests for
  all tiers, downgrade resistance, replay, revocation, and approval gates.
- `genesis/capabilities.py`: blocks lowering a required tier by supplying a
  deceptive `capability_level`, rejects unknown tiers and requires both C5
  limits.
- `genesis/engine_boundary.py`: Model Authorization Proof must match the
  exact capability requested.
- `tools/aurora_host_c1_reference.py`: existing bounded C1 Linux/systemd
  adapter; no C2–C5 execution path is introduced.

## Qualification before promotion, by gate

1. **C0:** deterministic policy regression, constitutional authorization,
   untrusted-input isolation, audit schema, negative side-effect tests.
2. **C1:** engine-signed grants, Angel binding, real measured cgroup enforcement,
   load/timeout/kill tests, restored sessions, least-privilege Linux host.
3. **C2:** per-resource allowlists, filesystem sandbox, verified rollback,
   concurrency/replay isolation, crash consistency, bounded resource accounting.
4. **C3:** scoped provider credentials, approval provenance, dry-run support,
   idempotency registry, rollback/compensation semantics and external audit.
5. **C4:** protected independent Motor admission, fresh challenge-bound
   hardware Angel attestation, one-use signed proof and operator approvals,
   hardware/key custody, incident-safe hold, external security assessment.
6. **C5:** C4 foundation plus durable quotas, expiry, cross-process and restart
   revocation, kill switch, exception path tests, time-bounded soak and
   independent adversarial qualification.

Higher-tier checks are **cumulative where applicable**, but C4 operations
may be inherently irreversible: they need critical approval/containment
rather than a dishonest claim of rollback.

## Do not use the simulator as production authorization

`Evidence` contains simulated Boolean outcomes for test scenarios.
Untrusted callers could set these to `True`: hence the reference has **no
dispatcher at any tier**, and C2–C5 return only `SIMULATED`. Even C0/C1
`POLICY_PASS` is not an execution receipt.

Private Aurora must verify Model proofs with a pinned trust root; Engine
authorization grants must be signed and one-use; Angel verdicts require
real independent attestation; approver identity and consent must be validated
by an independent service; revocation and quotas must survive restarts.
Keep Supreme control plane inaccessible and fail closed on missing evidence.

## Operational decision

Do **not** increase AWS `execution_tier`, modify private Motor or IAM grants,
or advertise C2–C5 execution as available until the corresponding target
qualification passes. See [Aurora qualification evidence](../architecture/AURORA_QUALIFICATION_EVIDENCE_2026_11_08.md).
