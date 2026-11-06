# Public beta release gate — 7 November 2026 (NZDT)

**Decision: HOLD for general-public onboarding.** Public website != approved public beta.

## Scope of first public beta

- Kyro web UI, reference Genesis text chat and bounded Realignment School diagnostics.
- Aurora C1 operations may report health to an authorized user; high-consequence Engine execution remains disabled.
- Do **not** market this as AGI, independently trained general model, proven consciousness, or production-grade infrastructure.

## Verified live foundation

- Sydney AWS account: enabled Kyro CloudFront distribution and two HTTPS HTTP APIs.
- Root research-chat user pool allows Cognito sign-up; V3 workspace pool remains admin-create-only.
- Both APIs protect private routes with Cognito JWT authorizers.
- Main V3 API stage throttled to 5 requests/second (burst 10); research API to 1 request/second (burst 3).
- Active Aurora Controller/Angel/Motor, Kyro core and School Lambda services; C1-only Aurora.
- Six CloudWatch metric alarms were created in Sydney during this release audit (Kyro API 5xx/4xx, Kyro Lambda errors, Aurora Controller errors, research API 5xx, research Lambda errors); **notification actions are disabled**, so alarms alone do not alert an operator.
- USD 1 AWS budget exists; it is an **alert, not a hard expenditure stop**.
- Source snapshot includes 18 deployed public browser objects, with S3 ETags and sizes; GitHub and AWS copies matched after merge.
- A CSP incompatibility in the Realignment preview was repaired in live S3 by externalizing JavaScript and CSS; the original HTML is backed up in S3.
- Candidate GitHub public-beta qualification and existing test suites passed.
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
