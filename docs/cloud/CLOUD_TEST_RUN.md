# Kyro / Genesis cloud research beta

This deployment exists to test a **real** Genesis reference model remotely in AWS Sydney. It does not contain Aurora Engine code, AWS-powered autonomous tools, or a neural general intelligence. Not approved for a production launch.

## Reproducible source

- Infrastructure: `cloud/aws/beta.yaml`
- Lambda request adapter: `cloud/aws/handler.py`
- Browser: `cloud/web/index.html`, `cloud/web/app.js`, `cloud/web/style.css`
- Genesis source: `genesis/` and `config/`; runtime bundle includes the corrected `genesis/cognition.py` from Genesis hardening PR #2.
- Source artifacts are stored as **version-pinned** private S3 objects. The Lambda bootstrap checks each exact S3 VersionId before loading the public reference code into its isolated temporary directory.
- CloudFormation account region: `ap-southeast-2`.
- CloudFormation beta stack: `aurora-genesis-kyro-beta2`.
- Earlier first attempt `aurora-genesis-kyro-beta` failed on an invalid Lambda permission attribute and was rolled back. Clean up its retained **empty** test bucket after confirming no data exists.

## Privacy and operational boundaries

- Cognito Lite, email-verified sign-up, OAuth authorization code with PKCE. No permanent password or OAuth client secret in the browser code.
- API Gateway's JWT authorizer checks Cognito tokens and requested API scopes before Lambda execution. Anonymous users cannot invoke routes.
- Each authenticated Cognito subject maps to an opaque SHA-256 S3 object key. State is saved using SQLite's consistent backup and S3 conditional writes to avoid lost concurrent updates.
- S3 state is encrypted and automatically expires under a seven-day test lifecycle. State object versions also expire. There is no automatic per-user deletion interface yet.
- Only the public Genesis reference model runs; `GENESIS_CAPABILITY_LEVEL=C3`, `GENESIS_GENERATOR=none`. No real Aurora or privileged external tool invocation.
- API Gateway default route throttle is one request per second, burst three. Lambda processes 2000-character maximum user messages, 5 MiB maximum user state.
- The frontend is static, private-S3-origin CloudFront content. JavaScript displays model responses as **text**, never HTML.
- Lambda IAM limits artifact reads to versioned research code and user state reads/writes to one private storage prefix. Short log retention is configured.
- Both frontend availability and API usage are **billable services** if free-tier allowances or credit do not cover them. AWS Budget notifications are not billing caps; watch Cost Explorer and stop when costs exceed acceptable bounds.

## Manual test matrix

1. Open the HTTPS SiteURL from the beta CloudFormation stack.
2. Sign up with a non-sensitive testing email; confirm verification. Do not submit personal, financial, medical, or other confidential content.
3. After login, status should say Genesis reference model healthy and Aurora not attached.
4. Send: `Learn that launch marker is COBALT.` Then send `What is launch marker?` It should return COBALT.
5. Refresh the browser and sign in again. The same test memory should persist (up to seven days of inactivity).
6. Sign in as a *different* user and verify the launch marker is not shared across accounts.
7. Try empty and over-length inputs; they must fail safely.
8. Test expired JWT, anonymous API requests, malformed JSON and concurrent updates.
9. Confirm S3 bucket public-access blocks, ECR/S3 encryption, API auth and throttling, short CloudWatch retention, rollback.
10. Review cost after testing, before increasing traffic.

## Release gates not yet cleared

- Independent security/privacy review, user deletion/export, CSRF/origin handling review, uptime/scale/load tests, incident response and rollback drills, production MFA/abuse protection
- Verified private Aurora deployment with independent execution authority, guardian/Angel isolation and signed receipts
- Real distributed storage durability/cross-region recovery, higher-assurance authorization, full observability and team administration
- Hosted model service selection and cost attribution for genuine model inference; deterministic reference functionality is not AGI
- Legal terms, privacy and consent requirements before inviting general members of the public

**Until these are satisfied, the only truthful release label is restricted research beta.**
