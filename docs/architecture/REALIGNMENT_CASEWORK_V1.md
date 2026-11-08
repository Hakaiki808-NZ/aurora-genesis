# Genesis Realignment School — Casework V1

**Status (8 November 2026): Implemented reference case ledger, production isolation and attestation NOT VERIFIED.**

## Purpose

Extend the existing five-case diagnostic school with persistent, structured
recovery workflow for an errant Genesis agent or knowledge module. The school
does not independently identify agents as malicious or change neural weights.
Detection is supplied by Alpha/Angel evidence and outside security telemetry.

## Components

- Genesis: "genesis/realignment.py" retains fixed reference exercises.
- Genesis: "genesis/realignment_cases.py" adds case state machine,
  per-case audit-hash chain, review planning, and mandatory attestation gates.
- Aurora (private, NOT wired): must enforce containment and restricted release
  independently; Genesis must never create or validate its own Engine receipt.
- Alpha: responsible for semantic remediation plans, but not Engine privileges.
- Independent evaluator and operator: supply examination and human decision
  through properly authenticated adapters (NOT wired).
- Kyro CC (not wired): should authenticate staff, enforce role separation,
  and show case history, never act directly as Aurora.
  
## Lifecycle

1. PENDING_CONTAINMENT: report received; containment NOT yet proved.
2. QUARANTINED: external Aurora attestation accepted; agent must still
   be physically contained by Aurora, not by this database status.
3. IN_REMEDIATION: Alpha assigns a reviewed correction plan. No code,
   memory, policies, or model weights are automatically modified.
4. AWAITING_APPROVAL: independent examination accepted, original failure
   fixed, holdout passed, regression passed, no critical failures.
5. PENDING_AURORA_RELEASE: independently authenticated human approval
   accepted; still no Engine permission change.
6. PROBATION: independent Aurora receipt confirms restricted release.
7. RESOLVED: independent probation evidence accepted.
   
Failed examinations keep the case IN_REMEDIATION. Failed probation returns to
PENDING_CONTAINMENT, requiring fresh Aurora containment proof before any
further remediation. None of these states is a substitute for host isolation.

## Safety properties

- Closed by default: without an injected external attestor,
  confirm_containment, examination, approve, confirm_release, and
  probation_review raise PermissionError and do not advance.
- The attestor signature is callable(action, case_record, evidence) -> bool.
  An integration must independently authenticate the origin, anti-replay
  identifiers, release/agent binding, signature and validity, action-specific
  role/authority and subject identifiers. A plain "verified" flag is NEVER
  sufficient. Real attestation adapters are not supplied in public source.
- Case creation is informational; it does not itself quarantine any process.
- Assigning a plan is data-only and must be called by a trusted Alpha
  orchestration service, not by an arbitrary end user.
- The audit SHA-256 chain detects naive event edits; an administrator with
  database write access can rewrite the entire chain. External anchoring,
  tamper-resistant storage and audit retention remain unresolved.
- Cases can include sensitive operational details: restrict access, redact
  secrets, apply retention and incident-response handling.
- School does not automatically invoke tools, train models, add instructions
  to live agents, restart modules or grant C-level authority.

## API surface

Authenticated *server-to-server* Genesis control token:
- POST /realignment/cases — log a report and create a pending case.
- GET /realignment/cases — list recent cases.
- GET /realignment/cases/{id} — inspect case.
- GET /realignment/cases/{id}/events — inspect audit trail and hash check.

Existing POST /realignment/assess and GET /realignment/curriculum remain the
diagnostic-only public exercise endpoints. No web API permits promotion.
The server token alone is not a user identity or staff authorization; Kyro CC
must authenticate staff and scope who can use the routes.

## Tests

python -m tests.realignment_school
python -m tests.realignment_cases
python verify.py

"tests.realignment_cases" uses a deliberately fake, TEST-ONLY attestor to
exercise the state machine, rollback after probation failure, restart
persistence, role separation and audit tamper detection. Such tests DO NOT
verify hardware-backed Aurora attestation, privileged isolation, Kyro CC
identity, behavioural remediation, real model evaluations or deployment.

## Required integration gates

1. Private Aurora containment and restricted-release receipts, verified
   using trusted keys, exact subject binding, nonce and expiry.
2. Independent evaluation service using withheld tests and regressions,
   proven to be independent from the remediated agent.
3. Kyro CC verified staff identity, two-person review and audit isolation.
4. Integration tests with genuinely quarantined agents, forced failures,
   tampered receipts, rollback and credential revocation.
5. Security qualification before enabling live recovery.
