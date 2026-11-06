# Seven User-Requested AI Capabilities: Integration Architecture

Date: 2026-11-07
Status: IMPLEMENTATION FOUNDATION (pre-alpha, not deployed)
Architecture: Kyro (authenticated interface) → Genesis (semantics) →
Aurora (runtime authority). No change to Supreme/Alpha/Omega/Angel boundaries.

## Why these methods

Reliable real-world task completion requires *observable success*, not
persuasive generated language. User preference and memory need explicit consent,
profile isolation, expiration and deletion. Proactive assistance should be
opt-in, actionable and nonintrusive. Source provenance needs links and
independent review instead of invented certainty. Decision support should
expose the user's own inputs and trade-offs.

References:
- NIST AI RMF measurement/oversight:
  https://airc.nist.gov/airmf-resources/playbook/measure/
- OWASP AI Agent Security Cheat Sheet:
  https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html
- W3C PROV-O provenance relationships:
  https://www.w3.org/TR/prov-o/
- AWS AgentCore Memory user preference concepts:
  https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/user-preference-memory-strategy.html
- AgentCore long-term vs retrieval:
  https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-ltm-rag.html
- MCP 2026-07-28 security/current architecture:
  https://blog.modelcontextprotocol.io/posts/2026-07-28/
- A2A protocol:
  https://a2a-protocol.org/latest/
- METR reliability methodology:
  https://evals.alignment.org/time-horizons/

## 1 — Actually finish work

Design: create a durable task, decompose into bounded steps, obtain explicit
approval for consequential steps, dispatch only through Aurora and obtain
attested *runtime* receipts. Validate acceptance criteria against independent
evidence; persist partial progress; expose blocked/recovery state.

Existing main branch has Genesis Planner and Aurora Engine Boundary.
The separate Outcome Assurance PR #25 introduces task state, criteria, and
human-attested evidence review. This branch does **not** merge PR #25; review it
separately before connecting to the execution pipeline.
Next integration: task_id + criterion_id + Aurora receipt_id + source snapshot
bound by immutable digest. Model cannot self-declare "verified".
Metrics: strict end-to-end success rate, duplicate external actions, human
correction rate, incomplete tasks erroneously labelled complete.

## 2 — Proactive help

Design: event source → consent check → relevance/due filter → user-visible
attention feed → optional notification orchestrated by Aurora after Kyro opt-in.
Avoid constant autonomous polling until explicit service limits and permission
checks exist.

Implemented: opt-in nudge storage, deterministic due filtering, dismiss action
and pull-only attention retrieval. No timers, push, emails or autonomous tool
calls. Kyro must authenticate user, respect quiet hours, prioritise and
deduplicate and make reminders easy to disable.

Metrics: useful nudges accepted, false/unwanted nudges, cost per useful alert.

## 3 — Personal recommendations

Design: explicit preference cards, provenance (user set vs inferred), TTL, and
review/override. Separate presentation preferences from high-risk financial,
medical or sensitive inferences. Retrieval creates context but must not
authorize action. Knowledge packs remain separately installed and licensed.

Implemented: explicit preference write, read, correction via upsert and forget,
subject to 'personalization' consent. No implicit preference extraction or
purchase decisions. The profile ID is supplied by a trusted constructor,
not a verified user identity.

Metrics: relevance judgments, edit/correction rate, unconsented inference rate.

## 4 — Accurate, verifiable answers

Design: source acquisition through approved retrieval tools, segment and
timestamp evidence, capture W3C-style provenance, independently check
references, detect contradictions, label unknown/unsupported, and have a
review/appeal process. A reference being present is **not** proof.

Implemented: claim/source-reference records with deliberately conservative
UNSUPPORTED/SOURCES_LISTED_UNCHECKED states and HUMAN_ATTESTED_SUPPORT/
HUMAN_DISPUTED reviewer states. No URL fetch, fact checking, source trust
scoring, cryptographic verification or calibrated probability in this branch.

Metrics: unsupported-claim fraction, citation validity, contradiction rate,
review reversal rate. Evaluate against independent ground truth.

## 5 — Context and continuity

Design: separate episodic conversations from durable preferences and semantic
facts. Only useful, consensual, bounded facts enter long-term memory; attach
owner, source, expiry, version and correction history, with per-profile search.
Consider memory-poisoning and invalid attribution explicitly.

Implemented: new consent-gated profile records for explicit memory and
preferences, expiry filtering, overwrite and deletion.
**Important:** the existing Genesis respond() still writes episodes/facts to
legacy shared Store independently. Revoking new UX consent does NOT stop or
erase those older paths. This is a deliberate compatibility boundary and a
blocker for any public privacy claim or multi-user launch.

Metrics: factual recall precision, stale-memory rate, cross-profile leaks,
deletion completion across all backups and derived data.

## 6 — Better decision support

Design: separate goals, hard constraints, alternatives, verified inputs,
user-specified priorities and sensitivity testing. Return an inspectable table
of contributions; user makes consequential decisions. Genesis Guardians
continue to evaluate any action request.

Implemented: deterministic non-acting weighted-sum comparator with validated
0–5 scores, nonnegative weights, full criterion coverage and tie ordering.
Scores are *user-supplied estimates*, not observations. No automated action.

Metrics: reproducibility, trade-off clarity, sensitivity to weight changes,
independent review against outcomes.

## 7 — Privacy, permission and control

Design: authenticate each user in Kyro, enforce tenant/user authorization
server-side, issue task/audience-bound credentials to Aurora, isolate memory
and tool context, offer export/revoke/delete, log sensitive actions without
retaining private content, support key revocation and delete-from-backups policy.

Implemented: 4 deny-by-default UX consent scopes (memory, personalization,
proactive, provenance), per-profile data queries, scoped revocation cleanup,
UX table export and erase. No auto-training or model-weight update.

**Non-goals / blockers:**
- This is not user authentication or multi-tenant isolation for the *whole*
  product. The legacy Store contains unpartitioned episodes, facts and goals.
- Profile identity remains a trusted constructor argument, not identity proof.
- No HTTP routes are exposed for these features until Kyro can authenticate
  users and enforce per-user ACLs. Existing older routes still need review.
- Logical DELETE from SQLite cannot guarantee removal from WAL, filesystem
  copies, backups, logs or third-party model providers.
- Do not call this "GDPR-compliant" or "fully private" without a separate
  threat/privacy/legal assessment.
- No automatic extraction of personal preferences from conversations.
- No model may consent on a user's behalf or change access permissions.

## Model API implemented

    Genesis(..., profile_id="local")
    ux_consents()
    ux_set_consent(scope, enabled)
    ux_remember(kind, key, value, source="user_explicit", expires_at=None)
    ux_recall(kind, query="", limit=30)
    ux_forget(kind, key)
    ux_add_claim(statement, sources=[])
    ux_review_claim(claim_id, supported, reviewer)
    ux_propose_nudge(title, due_at)
    ux_attention(now=None, limit=30)
    ux_dismiss_nudge(nudge_id)
    ux_compare_options(criteria, options)
    ux_export_profile()
    ux_erase_profile()

All UX operations are programmatic-only in this baseline.
A future Kyro gateway MUST inject profile_id derived from verified session
claims; never let a public request specify someone else's profile_id.
Never expose shared Store or control-plane credentials directly to browsers.

### Example

    from genesis import Genesis
    m = Genesis(state_path="state.db",workspace="workspace",
                enable_ollama=False, profile_id="trusted-local-operator")
    m.ux_set_consent("personalization", True)  # only after actual user permission
    m.ux_remember("preference","interface-theme","light")
    assert m.ux_recall("preference")[0]["value"] == "light"
    m.ux_set_consent("proactive", True)
    m.ux_propose_nudge("Check an approved milestone","2026-11-08T10:00:00+13:00")
    print(m.ux_attention())
    print(m.ux_compare_options(
        [{"name":"cost","weight":2},{"name":"speed","weight":1}],
        [{"name":"A","scores":{"cost":5,"speed":2}},
         {"name":"B","scores":{"cost":3,"speed":4}}]))
    m.close()

## Integrating with the existing three systems

Kyro:
- Issue verified first-party account/session token; enforce tenant_id+user_id.
- Show memory/preferences dashboard, consent toggles and hard delete/export.
- Render evidence cards clearly marked "unchecked" vs "human reviewed".
- Render decision comparison UI with editable weights and scores.
- Poll attention feed only when user enabled it; add quiet-hours.
- Bind protected task review to identity, not a caller-supplied reviewer string.
- Add plugin/knowledge-pack installation surface only with trust, license,
  publisher signature and entitlement checks.

Genesis:
- Use existing working/episodic/semantic/procedural memory separation;
  avoid silent promotion of arbitrary web instructions into durable memory.
- Keep the UX profile store separate from raw generation contexts until
  consent, context selection, TTL and untrusted-data controls pass.
- Wire task assurance (PR #25) to existing Planner and Retriever.
- Add evidence verification pipeline and confidence calibration.
- Gate inferred preferences behind user-visible suggestion/confirmation.
- Preserve Alpha/Omega semantic authorization on consequential plans.

Aurora:
- Provide durable jobs/scheduler, retries with idempotency keys,
  resource/cost ceilings and circuit breakers.
- Verify Model Authorization Proof and human approvals on each consequential
  tool call; never accept model text as authorization.
- Produce signed execution receipts for actual committed outcomes.
- Angels maintain independent runtime observation; Supreme remains
  operational and semantically blind.
- For tools use MCP auth/bound resources, for inter-agent delegation use A2A;
  neither protocol should circumvent local authorization.

## Integration order / completion gates

0. Baseline (this PR): new UX control-plane module, model methods, local tests.
1. Merge reviewed Outcome Assurance PR #25 or reconcile it with current main.
2. Implement Kyro end-user authn/authz, service-to-service identity and per-user
   rate limits. Audit and gate *all* legacy endpoints and raw Store reads.
3. Migrate legacy episodes/facts/goals to per-user scoped storage under explicit
   consent, retention and deletion policy; test erase across backups/WAL.
4. Connect Planner → task ledger → Aurora receipts → independent criterion checks.
5. Add real provenance validation, online retrieval, source timestamping,
   contradiction checks and independent evaluations.
6. Add opt-in scheduler + quiet hours + notification controls.
7. Shadow-test on synthetic data, perform red-team and privacy assessment,
   canary AWS deployment with fixed budget and rollback.

## Acceptance criteria before user-facing beta

- No cross-user data visibility in any endpoint.
- Every consequential action has valid task-scoped Aurora permission/receipt.
- Unverified evidence cannot be labelled verified.
- Revoke/delete effects measured and explained across all storage systems.
- No notifications without explicit opt-in; no unexpected cost/work loops.
- Full pre-alpha regression suite and adversarial cases green.
- Privacy/security review and documented incident recovery procedures.

No AWS resources were created or changed by this branch.
