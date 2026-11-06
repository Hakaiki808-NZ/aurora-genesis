# AWS private-alpha rollout gate — 2026-11-07 (NZDT)

**Release classification:** experimental private alpha; **not** a production Aurora Engine or AGI deployment.

## Current AWS boundary

- Public Kyro frontend: `https://d3j65cc3p66kzr.cloudfront.net/`
- Kyro V3 workspace: `/v3/index.html`
- Public backend health: `https://ces52hcf3e.execute-api.ap-southeast-2.amazonaws.com/api/v3/health`
- Protected backend routes: `/api/v3/{proxy+}` with API Gateway JWT authorizer
- Genesis: research-only Lambda behind a named, IAM-restricted internal invocation from Kyro. No verified independent trained checkpoint.
- Aurora: **execution disabled**. No protected engine authority is present in public Kyro or Genesis.
- Sign-in: Cognito private-alpha user pool is currently admin-create-only; browser end-to-end sign-in is not yet verified.
- Cost guard: US$1 AWS budget is an alert, **not a billing cap**. Do not enable paid inference or new standing resources by assuming free-tier eligibility.

## Automated public-edge checks

Run `python3 tools/aws_private_alpha_smoke.py` to verify:

1. Kyro landing page and V3 workspace are publicly reachable.
2. Public health is healthy and still reports Aurora execution disabled.
3. Anonymous requests to protected readiness, projects, and conversation-write routes are rejected at API Gateway.

CI runs this read-only smoke test on relevant pull requests and changes to `main`. No AWS keys, requests for tokens, persistent writes, tool execution or model inference are used.

## Remaining acceptance gates before inviting external users

- [ ] Register an explicitly authorized first test account; verify the real Cognito browser PKCE flow (no synthetic JWT claims).
- [ ] Verify authenticated Kyro → Genesis chat and conversation persistence using a real, permitted account.
- [ ] Confirm deployment rollback and recovery with an audited drill, and review CloudWatch telemetry without exposing user content.
- [ ] Validate AWS services, quotas, budget alerts, and an independently effective spending stop/disable procedure.
- [ ] Deploy the **private** Aurora implementation separately, with true workload isolation, authenticated receipts, independent Angel attestation, authorization-proof verification, replay protection, recovery, and revocable interlocks.
- [ ] Conduct penetration and failure tests before enabling any Aurora side-effectful operation.
- [ ] Only enable neural inference after account-approved nonzero quota, capped permissions, consent/data-handling review, and deliberate budget approval.

## Boundary

This document contains no secret credentials, private signing material, or security-sensitive Aurora implementation. Production qualification is a separate milestone from making the **research** frontend and model reachable.
