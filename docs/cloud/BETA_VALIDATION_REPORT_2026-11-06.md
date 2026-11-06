# Cloud research beta — verified test report (6 November 2026)

## Release classification

**Decision: GO for user-assisted, low-volume research beta test runs. NO-GO for production, public AGI claims, autonomous external tools or deployment of proprietary Aurora internals.**

- Region: AWS Sydney (`ap-southeast-2`)
- Base infrastructure stack: `aurora-genesis-dev-foundation` — `CREATE_COMPLETE`
- Application stack: `aurora-genesis-kyro-beta2` — `UPDATE_COMPLETE` after HTTP security headers
- Browser HTTPS entry point: `https://d3j65cc3p66kzr.cloudfront.net/`
- API base: `https://mex7yuj2j2.execute-api.ap-southeast-2.amazonaws.com`
- Reference code: public Genesis v0.1 plus PR #2 intent-context fix; all mutable tool authority remains subject to reference-model policy. No closed-source Aurora binary was deployed.
- Development PR: #7, intentionally **draft** and based on Kyro local alpha PR #3.

## Verified in connected AWS account

| Probe | Evidence | Verdict |
|---|---|---|
| CloudFormation | All application resources created and later security-header update completed | PASS |
| Genesis health | Direct Lambda invoked, all model self-checks true | PASS |
| Lambda authentication fallback | Synthetic direct invocation without claims returned 401 | PASS |
| S3 memory | Learned marker COBALT and recalled it in another Lambda invocation | PASS |
| Logical tenant isolation | Second synthetic subject did not retrieve the first subject's marker | PASS |
| Site HTTPS | Independent temporary AWS HTTP probe obtained HTTP 200 HTML | PASS |
| Frontend JS | HTTP 200 with JavaScript content type | PASS |
| Browser config | HTTP 200 JSON with public Cognito / API settings only | PASS |
| API absent auth | HTTP GET /api/status returned 401 before Lambda | PASS |
| API invalid token | Invalid bearer JWT returned 401 before Lambda | PASS |
| Cognito hosted login | OAuth authorize endpoint returned HTTP 200 login form | PASS |
| Valid Cognito access token | Two temporary verified test accounts received tokens | PASS |
| Real JWT-to-API path | Valid Cognito token returned 200 /api/status, healthy Genesis | PASS |
| Authenticated memory | Learned and recalled ZEPHYR across two authenticated API requests | PASS |
| Cross-account memory | Second Cognito account could not retrieve ZEPHYR from first | PASS |
| Temporary users | Two test accounts removed via Cognito AdminDeleteUser | PASS |
| Temporary infrastructure | IAM-only HTTP QA probe stack deleted; failed initial stack removed | PASS |
| CloudFront hardening | HTTPS redirect; CSP, HSTS, DENY framing, no-sniff, referrer headers attached | PASS |
| Cost protection | Monthly US$1 AWS Budget with existing email threshold alert | ALERT ONLY, NOT HARD CAP |
| Promotional credits | AWS organization service-control policy denies reading credit balance | UNKNOWN |

## Still requires human user-assisted verification

1. Open the website in a real browser.
2. Follow Cognito sign-up, email verification, OAuth code flow with PKCE, and redirect into Kyro.
3. Send and recall a test fact, refresh browser, sign in again and confirm access.
4. Check mobile layout, keyboard accessibility, browser logout and session expiry.
5. Report errors or screenshots from the real browser.

An HTTP 200 for Cognito's login page is not proof of the entire browser PKCE exchange. The manual UX test remains open.

## Critical limitations / public launch blockers

- This is deliberately bounded deterministic cognition, **not AGI**, and it is not backed by a frontier inference service.
- No private Aurora runtime, verified execution receipts, Angels, or tool-side operational authorization is integrated.
- Open self-registration with email verification is only appropriate for low-volume pilot tests: no CAPTCHA, mandatory MFA, complete abuse controls, or independent attack review.
- Automated account deletion/export, detailed retention policy, privacy impact assessment, and terms are not complete. Do not submit sensitive information.
- No load/soak testing, independent pentest, cross-region disaster recovery, incident management, production observability, or uptime qualification.
- The AWS Budget is a **notification**, not a spending limit. Cost Explorer data may lag. Credits have not been verified.

## Reproducibility

The Lambda function loads source from four S3 object versions pinned in stack parameters and validates the returned VersionId. `cloud/aws/beta.yaml` is the CloudFormation source, `cloud/aws/handler.py` is the runtime adapter, and `cloud/web/*` are the Kyro frontend sources. Source bundles are private; do not store signing keys or AWS credentials in GitHub.

To stop new browser traffic urgently, disable the CloudFront distribution; to stop model inference, disable the API Gateway stage or change Lambda reserved concurrency via an approved operational runbook. AWS Budgets cannot enforce a zero-dollar spending cap.
