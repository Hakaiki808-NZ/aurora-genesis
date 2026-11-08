# Aurora C2 — reversible sandbox execution candidate (8 November 2026)

**Status: reference implementation in PR, real AWS execution tier stays C1.**
This work responds to a request to allow higher execution without removing
Aurora's independent security boundary.

## One narrow capability

C2 allows **only** a bounded mutation of a locally managed, explicitly
provisioned SQLite workspace:
`sandbox:<namespace>/<resource_key>` (not an arbitrary filesystem path).

Operations:

1. `write` — replace or create a <= 4 KiB Unicode value with an atomic
   transaction, version increment and durable before-image receipt.
2. `rollback` — restore the previous value (or delete a newly created
   resource) only if the resource has not changed since the target write.

Each request must carry a short-lived, one-use, HMAC-protected *test* grant
bound to the subject, session, epoch, scope, key, action and payload digest.
Grant TTL must not exceed five minutes. Journal uniqueness rejects concurrent
replay; transactions protect rollback and per-scope key quotas.

There is **no** generic process execution, network IO, AWS mutation, external
credential access, host-file selection, privilege escalation, delete-all
endpoint, or ability to change Supreme / Angel / Motor controls.

## What the tests exercise

`tests/test_aurora_c2_workspace.py` commits actual sandbox writes and
restores, then rejects:
- unsigned payload changes, signature changes, impersonated issuers;
- attempts outside `sandbox:<namespace>` or scope/key tampering;
- unknown operations and arbitrary shell/privileged commands;
- replay (including concurrent attempts and cross-process reopened DB);
- cross-session rollback and rollback after conflicting newer writes;
- oversize payloads, quota breaches and symlinked database paths.

Unit test results support only this isolated reference design. A passing CI
runner is not proof of production Aurora's runtime isolation.

## Deployment qualification: requirements NOT yet cleared

- **Private Engine grant issuance and verification:** all real grants must be
  minted by Aurora after independent authenticated policy checks, signed or
  MACed with properly protected, rotated keys. The public `TestEngineSigner`
  must never be exposed to Genesis, Kyro or untrusted clients.
- **Operator-owned sandbox:** an approved service account, dedicated data
  directory, least-privilege filesystem access, memory/CPU/IO constraints,
  protected key custody, kernel containment, clear tenant isolation.
- **Identity binding:** verify JWT/verified human approval (as applicable),
  Model authorization proof, Engine epoch/session/scope and one-use grant
  against authoritative server-side state; a request field is not proof.
- **Operational evidence:** crash/failure injection, concurrent race tests,
  durable restore, complete backup policy, immutable evidence, quota alarm,
  negative tests through the *actual* Controller → Admission → Angel → Motor.
- **Release authorization:** only then allow an explicit scoped `C2`
  operation on a private test deployment. Do not raise global
  `execution_tier` by configuration alone.

No new C2 AWS endpoint, Motor handler, IAM privilege or public route has been
enabled. Hardware-backed Angel attestation and C4/C5 execution remain separate
blocked qualifications; C2 must never be used to route around them.

**Naming:** The project's separate C/B/A achievement standards (C5=B1,
B5=A1) do not grant Engine execution authority. This file concerns legacy
Aurora execution-policy tier C2, not model capability attainment.
