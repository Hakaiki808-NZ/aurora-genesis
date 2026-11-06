# Genesis Outcome Assurance v0 (pre-alpha)

A small, evidence-backed task state machine added to the **public Genesis**
reference implementation. This is not a general autonomous agent, not the
Aurora execution kernel, and not a production-ready permission system.

## Purpose

Prevent a model from treating "I wrote an answer" as "the requested real-world
work is complete." Each task has explicit acceptance criteria and must have
human-reviewed evidence for **every** criterion before an explicit human
completion confirmation is recorded.

State flow:

    DRAFT --approve--> APPROVED --start--> WORKING --review--> REVIEW
                           |                     ^          |
                           |                     +--revise--+
                           +----block--> BLOCKED --start----+
    DRAFT/APPROVED/WORKING/REVIEW/BLOCKED --cancel--> CANCELLED
    REVIEW --(all criteria accepted + explicit confirmation)--> COMPLETED_ATTESTED

- "approve" approves the **tracking plan only**; it does not authorize spending,
  network activity, external tool invocation, or irreversible actions.
- Evidence submissions are PENDING until manually accepted/rejected. Source type
  labels are *claims*, not authenticated provenance.
- The completed state means **reviewer attestation**, not independent truth.
- All transitions, evidence additions and reviewer decisions are written to an
  append-only application event table (not a tamper-evident ledger).
- Rows live in the same SQLite file as Genesis Store. SQLite backup includes
  them. The older JSON export endpoint **does not** include the new tables.

## Model API

    model.create_task(title, criteria, priority=50, due_at=None)
    model.tasks(limit=100)
    model.task(task_id)
    model.due_tasks(now=None, limit=100)
    model.task_attention(now=None, limit=50)
    model.task_events(task_id)
    model.transition_task(task_id, action)
    model.add_task_evidence(task_id, criterion_index, observation, reference, source_type="user")
    model.review_task_evidence(task_id, evidence_id, accepted, reviewer)
    model.complete_task(task_id, reviewer, human_confirmed=False)

Criterion indices are zero-based. due_at must be ISO-8601 with timezone;
all timestamps are normalised to UTC. Priority is 0–100.

## HTTP routes

All routes below require a backend-only header:

    X-Genesis-Control-Token: <secret>

Set GENESIS_CONTROL_TOKEN to an independently generated 32+-character secret.
Without it, the routes return 503; an incorrect token returns 401.

    POST /tasks
      {"title":"Publish release","criteria":["CI green","Endpoint responds"],
       "priority":70,"due_at":"2026-11-08T10:00:00+13:00"}
    GET  /tasks
    GET  /tasks/due
    GET  /tasks/attention
    GET  /tasks/{task_id}
    GET  /tasks/{task_id}/events
    POST /tasks/{task_id}/transition
      {"action":"approve"}  # approve | start | review | revise | block | cancel
    POST /tasks/{task_id}/evidence
      {"criterion_index":0,"observation":"Tests passed","reference":"CI run URL",
       "source_type":"tool"}
    POST /tasks/{task_id}/evidence/{evidence_id}/review
      {"accepted":true,"reviewer":"authenticated-operator-id"}
    POST /tasks/{task_id}/complete
      {"reviewer":"authenticated-operator-id","human_confirmed":true}

Kyro may poll /tasks/attention and /tasks/due **after authenticating** users.
No background jobs or unsolicited notifications are included. Attention
reasons: blocked, overdue, human_review, approval_required, ready_to_start.
Items are suggestions only, never self-authorised actions.

## Trust / separation / deployment

- AURORA still governs tool runtime, side-effects and Engine receipts.
- Genesis can propose plans and record evidence but this module **never**
  invokes tools or issues an Engine request.
- Kyro must mediate end-user authn/authz, tenancy, and user identity. Do not
  embed GENESIS_CONTROL_TOKEN in client-side HTML, mobile apps or browsers.
- The shared control token is **not** multi-user authentication. It protects
  the standalone pre-alpha control plane only. Do not publish it directly on
  the internet. Private localhost/staging only until per-user authz and audit
  of other legacy endpoints are complete.
- External references are not fetched or independently validated.
- Reviewers are self-reported strings in this baseline. The system cannot
  prove an actual human reviewed evidence until identity is externally bound.
- Never infer that a TaskLedger status implies deployment/financial actions
  occurred; confirm through Aurora receipts and real-world verification.
- Do not put secrets or sensitive personal data into criteria/evidence.

## Testing

    python -m tests.task_assurance
    python verify.py

The regression suite checks rejection of premature completion, partial
evidence, state bypass, overwritten reviews, persistence, cancellations, UTC
deadlines, and overdue attention suppression after completion.

## Next milestones (not implemented)

1. Bind accepted evidence to an Aurora-authenticated, non-replayable receipt.
2. Let Kyro authenticate a real human reviewer and enforce per-user task ACLs.
3. Integrate the existing goal planner and bounded tool execution with task
   state, without letting Genesis directly dispatch consequential actions.
4. Add optional reminders only with explicit scheduling/notification consent.
5. Add measurable end-to-end success benchmarks, rollback and human escalation.
