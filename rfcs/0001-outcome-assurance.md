# RFC 0001: Evidence-backed task outcomes and pull-only attention

Status: PROPOSED (November 2026)
Area: Public Genesis Model API; Kyro-facing contracts
Author: project implementation proposal

## Problem

Chat-oriented systems can claim a task is done when they have merely generated
a plausible answer. In long-running user work, this results in misleading
completion signals, forgotten next actions and repeated context.

## Decision

Add a small durable task ledger in Genesis with explicit acceptance criteria,
a bounded state machine, unreviewed evidence submissions, human decision
records and a pull-only task attention feed.

Do NOT let this layer dispatch privileged external actions, mint Aurora
execution authority or claim independent verification. Use
COMPLETED_ATTESTED rather than VERIFIED.

## Alternatives considered

- A free-form autonomous agent with direct tools: rejected for this iteration;
  weak completion semantics and greater risk.
- Storing tasks as chat messages only: rejected; not durable or auditable.
- Automatic evidence acceptance from model explanations: rejected;
  self-verification is circular.
- A background notification service bundled into Genesis: rejected for v0;
  scheduling and consent belong to Kyro plus authorized operational services.

## Compatibility

Adds task_assurance.py and optional task routes/methods. Does not modify
existing Engine Contract, Guardian authority or existing goal execution.
Data is stored in independent assurance_* tables inside Genesis SQLite.
Existing schema version and public v0.1 semantics remain unchanged.

## Security and privacy

Task control HTTP endpoints are disabled until a backend shared secret of
32+ characters is configured; they are not browser-facing public endpoints.
Kyro must add user authentication/authorization and tenancy. Reviewer names
are unauthenticated claims at this stage; accepted evidence is not a proof
of real-world success. Do not store private credentials in task observations.

## Acceptance gate

- Existing Genesis verification suite passes.
- New tests reject completion without evidence or explicit confirmation.
- Incomplete/rejected review paths remain revisable.
- No external tool execution path introduced.
- Due/attention feed never reports completed tasks.
- API control routes reject missing and invalid credentials.
- Manual security and deployment review prior to public enablement.

## Future revisions

Aurora signed receipts bound to task criteria; independent source validation;
Kyro-authenticated human review; per-user memory consent; opt-in proactive
reminders; autonomous tool use only through audited, bounded Engine flows.

See docs/architecture/TASK_OUTCOME_ASSURANCE.md and
docs/research/AI_USER_WISHES_2026.md.
