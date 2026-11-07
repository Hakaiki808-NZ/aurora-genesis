# Proposed Quantum Job Contract v0 (research / not a deployed Aurora contract)

**Status:** Draft. **Scope:** side-effect-free CPU simulator prototype now; potential managed simulators and QPUs only after independent Aurora approval.

## Request envelope

The current local-only `run_reference_job` accepts these exact fields:

```json
{
  "kind": "maxcut",
  "backend": "reference-cpu",
  "shots": 1024,
  "seed": 20261107,
  "grid_points": 17,
  "max_cost_usd": 0,
  "problem": {
    "qubits": 3,
    "edges": [[0, 1, 2.0], [1, 2, 2.0], [0, 2, 1.0]]
  }
}
```

For Bell test, `kind="bell"` with no `problem` or `grid_points` fields. Invalid fields and non-finite numbers fail closed. Limits: 2–6 qubits, at most 15 unique edges, weights in (0,1000], 1–4096 shots, 3–25 grid points per angle, at most 625 grid evaluations. The host-injected `ReferenceAdmission` may tighten limits. The local dispatcher rejects every paid or remote backend; it never makes a cloud call. **ReferenceAdmission does not provide real Aurora authentication or security.**

## Proposed real Aurora envelope — NOT IMPLEMENTED

A future authenticated Engine Request would include:

- `quantum_job_id` UUID and stable `idempotency_key` bound to authenticated tenant identity
- `caller_id`, `tenant_id`, `approved_project_id` derived from verified Kyro token (not accepted as a trusted model-supplied claim)
- `job_kind`, circuit/source digest, declared qubits/gates/depth/shots/resource and deadline limits
- `backend`, region, immutable device target and explicit `estimated_max_cost_usd`
- Data sensitivity classification, permitted data region and retention policy
- Model semantic decision and action-bound Model Authorization Proof where applicable
- Separate **Aurora-issued** admission decision, lease, revocation and cost reservation

Lifecycle: `PREPARED` -> Aurora `ADMITTED` -> `QUEUED` -> `RUNNING` -> terminal `COMMITTED` / `FAILED` / `CANCELLED`. The last three map to the existing `EngineReceipt` statuses; a quantum algorithm's numeric score is never proof that the Engine committed its side effect. Source provenance and request/result digests should be tracked with protected telemetry.

## Denial policy

- No JWT/authenticated tenant, no human permission for paid/external execution, missing model proof when applicable: reject.
- No physical QPU/remote simulator without an Aurora-owned enabled backend, budget reservation and region allowlist.
- Refuse negative/non-finite price estimates, unsupported devices, unknown job types, unbounded iterations and retries.
- Reject untrusted arbitrary generated scripts; use structured schema or parsed whitelisted OpenQASM subset.
- No model-generated override of Supreme/Guardian/Angel operational controls.
- Always retain **classical fallback**, including when circuit execution fails or data residency prohibits cloud.

## Kyro proposal — NOT IMPLEMENTED

- `POST /quantum/jobs` (authenticated, operator-approved for external jobs)
- `GET /quantum/jobs/{id}` (tenant-bound)
- `GET /quantum/jobs/{id}/results` (tenant-bound, source/method metadata)
- `POST /quantum/jobs/{id}/cancel` (authorised, best-effort after remote submission)

Avoid exposing raw AWS credential material or hidden Engine security internals through Kyro. Backend type and algorithm labels must be clearly disclosed so that users do not mistake simulated results for a physical quantum computation.
