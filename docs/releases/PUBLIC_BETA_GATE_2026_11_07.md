# Public beta release gate — 7 November 2026 (NZDT)

**Decision: HOLD for general-public onboarding.** Public website != approved public beta.

## Scope of first public beta

- Kyro web UI, reference Genesis text chat and bounded Realignment School diagnostics.
- Aurora C1 operations may report health to an authorized user; high-consequence Engine execution remains disabled.
- Do **not** market this as AGI, independently trained general model, proven consciousness, or production-grade infrastructure.

## Verified live foundation

- Sydney AWS account: enabled Kyro CloudFront distribution and two HTTPS HTTP APIs.
- Both the research-beta and private-workspace Cognito pools now require administrator-issued invitations (AWS change verified 7 November 2026).
- Both APIs protect private routes with Cognito JWT authorizers.
- Main V3 API stage throttled to 5 requests/second (burst 10); research API to 1 request/second (burst 3).
- Active Aurora Controller/Angel/Motor, Kyro core and School Lambda services; C1-only Aurora.
- Six CloudWatch metric alarms were created in Sydney during this release audit (Kyro API 5xx/4xx, Kyro Lambda errors, Aurora Controller errors, research API 5xx, research Lambda errors); **notification actions are disabled**, so alarms alone do not alert an operator.
- USD 1 AWS budget exists; it is an **alert, not a hard expenditure stop**.
- Source snapshot includes 18 deployed public browser objects, with S3 ETags and sizes; GitHub and AWS copies matched after merge.
- A CSP incompatibility in the Realignment preview was repaired in live S3 by externalizing JavaScript and CSS; the original HTML is backed up in S3.
- Candidate GitHub public-beta qualification and existing test suites passed.
- The existing 6 November cloud research-beta validation report records successful **real Cognito-issued JWT -> API Gateway -> Lambda -> Genesis** requests, per-user persistence and cross-account isolation using two subsequently deleted test accounts. Full human browser PKCE and V3 workflow verification are still pending.
- GitHub CI for existing reference model previously passed; this branch adds static and anonymous public-edge checks.

## Mandatory user-facing acceptance before opening broadly

- [ ] Test real Cognito PKCE sign-up/sign-in in an actual browser (both root beta and invite-only V3).
- [ ] With a permitted test account, verify chat, replay, persistence, edit and read-back with a second account proving isolation.
- [ ] Define privacy notice, user terms, retention and delete-account/data flow; do not collect personal/sensitive data before review.
- [ ] Verify accessibility, mobile usability and keyboard navigation.
- [ ] Demonstrate explicit honest description of deterministic/research-mode capability and engine restrictions.
- [ ] Complete abuse, concurrency, rate-limit and input-safety assessment; use conservative signup volumes.

## Mandatory operational acceptance

- [ ] Run and record public-edge CI with no failures.
- [ ] Configure an actionable alarm destination/operator and run a simulated failure notification.
- [ ] Record deployment/rollback and restore drill for Kyro, data, and Aurora control state.
- [ ] Review IAM scopes, API token authorization, cross-user data isolation, CloudFront origin and storage access, and threat model.
- [ ] Verify independent cost stop/disable procedure, quotas, and current account permissions before wider enrollment. AWS rejected a proposed reserved-concurrency cap for the research Lambda because the account must retain 10 unreserved executions; no concurrency change was made. The research API remains throttled at 1 request/second, burst 3.
- [ ] Check DynamoDB restore strategy: inspected Kyro and Aurora tables do not yet have point-in-time recovery enabled. Enable only with explicit cost acceptance.
- [ ] Implement a tested incident response, contact and response policy.
- [ ] Validate hosted neural model quota, per-request max tokens, cost ceilings and access before enabling inference; do not infer model quality from test harness passes.
- [ ] Do not turn on Aurora side effects until the full private hardened engine has independent security and recovery qualification.

## Rollback and launch choice

Keep current static CloudFront assets, JWT authorizers and restricted Aurora settings unchanged while gates are open. Use the existing S3 versioned/backup copies for rollback, but **test** recovery before relying on it. Public beta promotion requires a recorded go/no-go decision after the gates above, not a version-label change alone.

Source-control snapshot: `cloud/public-beta-web/`. It captures browser assets only, not the backend source or protected AURORA code.

## 7 November 2026 — invite-only AWS beta cutover audit

Verified in the connected Sydney AWS account:
- The research beta Cognito pool was changed via CloudFormation change set `kyro-beta-invite-only-20261107`; only the `BetaUserPool.AdminCreateUserConfig` property changed. Stack returned `UPDATE_COMPLETE`, and `AllowAdminCreateUserOnly=true` was read back.
- Public `/site/developers.html`, `/site/dev-login.html`, `/site/api.html`, and `/site/docs.html` now show an invitation-only notice. Public navigation was updated to beta sign-in. Previous S3 objects were copied under `backups/private-beta-cutover-20261107/site/` before editing.
- CloudFront invalidation `ICDF6Q11P6Y4GWYJCNKLICFX5P` returned `Completed`. GitHub source change `484a2c896af65399df302d8c0145ff46de9f97d9` passed the public-site and general tests.
- Cognito authorizer/client mappings match for the research-root and private V3 apps, and the Kyro V3 health Lambda returned an operational reference-mode response. These are not substitutes for real browser PKCE tests or full authenticated end-to-end checks.
- Bedrock Nova Micro Converse returned `ThrottlingException: Too many tokens per day`. External neural inference remains disabled; neither a model catalogue entry nor deployed Lambda proves successful live neural inference.
- The bounded `genesis-controlled-cpu-lora-dev` CodeBuild job completed successfully and uploaded a candidate adapter under `genesis/training/automation/runs/20261107-904d9cd81259/`. Daily human-approved-dataset checks are enabled; candidate training is not automatic publication or promotion to a live model.
- USD 1 monthly AWS Budget is an alert only; existing running EC2 instance `Server0` is outside this beta qualification and was not modified.

**Launch decision remains HOLD** until browser sign-in, live authenticated chat, data isolation, privacy, incident alerts, rollback drills, inference quality and per-account spend safeguards are independently validated. AWS is the selected sandbox and deployment target, but the Aurora/Genesis/Kyro full product is not yet completely integrated or production-verified.
