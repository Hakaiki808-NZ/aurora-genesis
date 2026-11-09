# Genesis always-on operation and Aurora targeted recovery

Status: public **reference design** and implemented **Genesis health endpoints**.
This document does not claim the closed-source Aurora supervisor, Kyro
authenticated session rehydration, or an AWS long-lived inference service has
already been deployed.

## Objective and boundary

Operate Genesis continuously without scheduled restarts. Aurora owns health
observations, load-balancer membership, fault isolation, restart authorization,
retry limits, and audit. Genesis owns model execution, semantic checks and its
persistent state. Kyro owns identity, authorization, browser reconnection and
the user's conversation presentation. Aurora sensors receive only opaque
component IDs, status codes, timing and resource metrics: never prompts,
responses, identities, raw memories, or model interpretation.

**Do not** make Genesis or Kyro able to restart Aurora, grant execution
privileges, or override an Aurora interlock. Model health endpoints expose no
actions. A successful health probe never constitutes an Engine authorization.

## Health contract

- `GET /health/live` -> HTTP 200 if the Genesis HTTP worker can respond.
  This is a **liveness** probe, not evidence the model can answer requests.
- `GET /health/ready` -> HTTP 200 with
  `{"component":"genesis","status":"ready"}` only when the model's existing
  self-check, including persistent SQLite integrity, succeeds. Returns HTTP
  503 and `status: unavailable` on failed checks or exceptions. Use for
  traffic eligibility. This endpoint is intentionally free of memory content.
- `GET /health` remains for backward compatibility, but must **not** be used
  as Aurora's readiness contract: the legacy response reports `ok` even
  when dependencies might be unavailable.
- `GET /diagnostics` remains separate. Gate diagnostic access to trusted
  operators at the ingress; do not expose it as a public control-plane feed.
- External neural backend failure is **degraded capability**, not evidence
  that the core Genesis process is corrupt. Monitor neural inference
  separately; do not kill healthy memory or knowledge services to fix a
  provider-side timeout.

On a target cluster, maintain independent probes for each inference worker,
database, queue, Kyro gateway and authentication dependency. Do not restart
all systems based on a single shared dependency failure.

## Aurora recovery decision table

| Observed condition | Action | Preserved state |
| --- | --- | --- |
| Healthy worker | No restart | Everything |
| One worker fails liveness three consecutive probes | Remove that worker from routing; restart only that worker with bounded backoff | Committed memory, session journal |
| Worker live, fails readiness three probes | Drain it, check the dependency first, then recycle it only when a local fault is confirmed | Durable store and queued turns |
| Neural backend unavailable | Mark neural capability degraded; circuit-break provider calls | Genesis core and Kyro sessions |
| Shared database unavailable | Fail closed on writes, avoid mass restarts, alert and restore storage first | Previously committed memory |
| Kyro frontend loses connection | Reconnect with jitter and re-fetch only authorized session history | Session identity and messages |
| Repeated worker crashes | Quarantine worker, cap retries, alert operator; no restart storm | Persistent state |
| Aurora supervisory plane unavailable | Preserve last signed policy and fail closed on privileged operations | Durable data; no unauthorized execution |

Suggested initial thresholds (tune using measured data): probe every 10s,
3 consecutive failures before isolation, 30s grace for cold starts, exponential
restart backoff beginning at 15s capped at 5m, quarantine after 5 restarts
in 15m, manual clearance or verified fault resolution. These are targets,
not measured SLAs.

During deployments: start replacement -> verify readiness -> switch routing ->
drain in-flight requests -> terminate old worker. Never reload all workers at
once. Handle long-running inferences with request IDs and bounded timeouts.

## Memory continuity and acknowledged turns

The local Genesis reference persists memory to SQLite in WAL mode, and
`Genesis.close()`/new `Genesis(state_path=...)` can reopen the same durable
state. A local disk path is **not** shared multi-instance durability; don't
run two hosts against one copied SQLite file. Run an authenticated and
partitioned database service before multi-user, multi-host operation.

For production Kyro -> Genesis interactions:

1. Kyro verifies an existing Cognito session; derive tenant_id/user_id from
   validated claims, never from a client-submitted field alone.
2. Assign conversation_id, turn_id, and idempotency_key; store each incoming
   turn durably as `accepted` **before** dispatch. Do not acknowledge it before
   the commit succeeds.
3. Dispatch a bounded inference request; store the completed response
   transactionally as `completed`, then acknowledge to the client. Retry an
   incomplete `accepted` turn with the same idempotency key and prevent
   duplicate side effects by checking Aurora action/receipt IDs.
4. After worker failure, Kyro re-fetches authorized turns and renders
   `completed` history; `accepted` turns become resumable or explicitly
   failed, never silently lost. Response streaming checkpoints are optional
   and must not be confused with final durable completion.
5. User sessions must not depend on the lifetime of a model worker. Use
   short-lived verified access tokens and server-managed refresh/session
   facilities; no raw refresh tokens, prompts, or secrets in browser local
   storage. Invalidate revoked sessions and apply rate limits.

**Security blocker:** the public `Genesis.respond()` currently writes legacy
episodes without authenticated-user partitions. Do not expose that singleton
as a multi-tenant production service or replay one user's turns into another
user's context. Create a scoped conversation/memory repository and migration,
with encryption, retention controls and access-control tests, first.

For the AWS beta in `ap-southeast-2`, Lambda instances are ephemeral; an
Lambda function is not a 24/7 resident GPT worker. Recover individual failing
invocations and watch alarms/queues. Deploy a separately isolated persistent
inference service only after storage, tenancy, auth, and Aurora interlocks
pass acceptance tests. DynamoDB PITR is not equivalent to session recovery;
enable and verify backups for the relevant production tables as a separate
reviewed change.

## Acceptance gates

- Repeated health probes do not change Genesis memory or invoke external tools.
- Terminating one worker leaves other workers able to serve.
- Local state is available after worker close/reopen. The reference regression
  test exercises this, but does not certify multi-host disaster recovery.
- A failed storage integrity check yields HTTP 503 readiness; never HTTP 200.
- Backend outage yields explicit degraded neural mode without restarting a
  healthy Genesis core.
- A committed turn is visible after simulated worker termination and Kyro
  reauthentication; no cross-user data leakage or duplicate external actions.
- Burst crashes trigger backoff/quarantine; absence of Aurora doesn't grant
  Genesis more authority. All recovery decisions produce sanitized audit events.
- Restore drill verifies backup consistency, auth, model version compatibility,
  and replay behavior before any public-beta readiness claim.

## Operational implementation status

Implemented in this public change: sanitized health routes, recovery/state
regression, documentation. Still required in the private Aurora runtime:
supervisor, alarms, bounded replacement and protected recovery audit.
Still required in Kyro: authenticated tenant-partitioned durable turn journal
and reconnect/resume UI. Production claims require real fault-injection and
restoration testing on the deployed stack.
