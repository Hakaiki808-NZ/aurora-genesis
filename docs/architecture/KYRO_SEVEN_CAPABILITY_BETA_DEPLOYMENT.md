# Kyro Seven-Capability Private Beta — Deployment Record

Date: 2026-11-07 NZDT
Region: ap-southeast-2 (Sydney)
Status: **Deployed for authenticated private-beta use; not production-complete.**

## Verified infrastructure

- CloudFormation stack: kyro-seven-capabilities-private-beta
- Lambda: kyro-seven-capabilities-beta (Python 3.12, 128 MB, 12s timeout)
- IAM role: kyro-seven-capabilities-beta-role
  - DynamoDB GetItem/Query/PutItem/DeleteItem restricted to:
    kyro-v3-data-dev and keys beginning with UX#
  - CloudWatch log stream permissions only to own log group
- Log retention: 7 days
- HTTP API: kyro-v3-core-dev, ces52hcf3e
- New route: ANY /api/v3/capabilities/{proxy+}
- Authorization: existing Cognito JWT authorizer beta-cognito-jwt (id 1ch8f6)
  with issuer ap-southeast-2_Pq71kumUV, administrator-created users only.
- No Lambda function URL; API Gateway JWT is required.
- API base: https://ces52hcf3e.execute-api.ap-southeast-2.amazonaws.com/api/v3/capabilities
- CloudFront: d3j65cc3p66kzr.cloudfront.net, distribution E3P0BZ3PPWYCO
- Site: https://d3j65cc3p66kzr.cloudfront.net/v3/index.html
- Navigation: sign in via existing PKCE; choose AI Capabilities.
- S3 source bucket: aurora-genesis-kyro-beta2-frontendbucket-a45mzzicqfvk
- Modified keys: v3/index.html, v3/app.js
- New keys: v3/capabilities.js, v3/capabilities.css
- Pre-change backups: v3/backups/2026-11-07-before-seven-capabilities/
- CloudFront invalidation IE49XJ4P7X8RPDOAL7TEP22VX6: Completed.

## Source of truth

- tools/aws/kyro_capabilities_lambda.py — CloudFormation inline Lambda.
- web/kyro/v3/ — versioned copies of deployed frontend.
- genesis/task_assurance.py, genesis/user_capabilities.py — Model
  reference implementations; these are not directly invoked by the deployed
  Kyro Lambda and must not be described as production-authoritative.
- tests/kyro_capabilities_lambda.py — offline simulated DynamoDB checks.
- tests/task_assurance.py, tests/user_capabilities.py — Model tests.
- verify.py and .github/workflows/tests.yml — test suite including JS syntax.

## Live verification results

CloudFormation CREATE_COMPLETE and scoped code UPDATE requested.
API Gateway route reports AuthorizationType JWT and the expected Cognito
authorizer. Lambda direct-invocation without claims returned HTTP 401.
Live synthetic Lambda tests: 27/27 checks passed, covering all capability
flows, premature-completion rejection, permissions and synthetic cleanup.
No real customer's session/token was used in those tests.

CloudFront reports enabled/Deployed; all four asset objects were present in
S3 and invalidation Completed. Browser login and an authenticated live
browser workflow were NOT independently exercised; operator acceptance is
needed for that final step.

## Capabilities shipped

1. Task ledger with user acceptance criteria, evidence and human attestation.
2. Opt-in due reminder/attention feed (pull-only).
3. Explicit user-set preferences.
4. Claim and source-reference review with *unchecked* vs *human-attested* states.
5. Explicit, user-set memory records and correction/forget.
6. Deterministic weighted option comparison (subjective inputs only).
7. Consent controls, scoped export, revoke and erase of beta records.

All feature records are stored under a server-derived Cognito subject key;
the browser never chooses another user's account ID. The user cannot enable
Aurora execution authority through these controls.

## Explicit limitations

- No general-purpose reliable autonomy or actual tool execution from tasks.
- No proactive timers, email/push delivery or cross-platform automation.
- Sources are not fetched or independently checked.
- Preference/memory entries are not automatically injected into the existing
  Genesis chat, and user consent does not govern older legacy memory tables.
- Erasure covers the new UX# records in Kyro's DynamoDB table only, not
  existing chat, provider logs, backups, CloudWatch, or already-trained weights.
- Reviewer identity is the caller's signed-in identity, not external
  verification that their cited evidence is correct.
- Consent deletion and S3 updates are not atomic cross-service operations.
- An account's existing AWS budget was $1 USD; AWS Budgets is an alert,
  not a hard spending cap. No high-cost GPU/Bedrock services were enabled here.
- Production security assessment, accessibility/browser acceptance testing,
  rate limits, data lifecycle audit and real Aurora execution receipts remain
  prerequisites for a public launch.

## Operational rollout / rollback

Deploy changes through the named CloudFormation stack (never through public
unauthenticated Function URLs). The stack's existing API Gateway JWT
authorizer must be retained on every capability route. Any change to scope
or issuer requires a security review. Exposing a direct Lambda URL would
bypass the intended Gateway authorization and is forbidden.

To revert frontend integration: restore v3/index.html and v3/app.js from
the two versioned S3 backups; invalidate the four CloudFront paths. Do not
automatically delete new user records during frontend rollback.

To disable the backend: remove or disable the capability route through an
approved stack change, leaving DynamoDB records intact for explicit retention
or deletion instructions. Do not delete the shared kyro-v3-data-dev table.

## Next release gates

- Human browser login and task flow end-to-end on Chrome/mobile.
- Security and privacy review; all legacy storage isolated per user.
- Rate limiting and cost alarms beyond simple AWS budget notifications.
- Provenance checking and verified Aurora receipt-to-criterion binding.
- Consent-based inference/memory usage by Genesis.
- Opt-in reminders delivered using an explicitly budgeted scheduler.
