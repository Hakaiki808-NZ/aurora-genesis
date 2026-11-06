# Kyro AWS workspace V5 — private alpha source snapshot

This directory contains the exact HTML, CSS, and JavaScript deployed to the existing AWS Sydney Kyro workspace on 6 November 2026.

- Workspace: https://d3j65cc3p66kzr.cloudfront.net/v3/index.html
- API: https://ces52hcf3e.execute-api.ap-southeast-2.amazonaws.com
- Live S3 object prefix: `v3/` in the existing Kyro frontend bucket.
- Sign-in: Cognito Hosted UI, PKCE; an administrator-created account is required. There are no enrolled users at this snapshot.
- Existing backend health check: operational, Genesis deterministic research reference, Aurora execution disabled.
- Frontend polish: system-state cards, accessibility/focus refinement, responsive layout and explicit alpha disclosure.
- Browser end-to-end sign-in has not been verified.
- No production launch or AGI claim is made.

**Security boundary:** This branch contains browser assets only. The private Aurora implementation, protected interlocks, signing keys and recovery mechanisms remain excluded. The public Cognito app client ID is not a client secret.

**Launch blockers:** account onboarding / live browser PKCE smoke test; Bedrock model inference quotas; independent protected Aurora runtime and Angels; complete auth/isolation and recovery testing; operational alerts, security review, cost guardrails and release qualification.

**Rollback:** A copy of the HTML and CSS before visual polish is stored under `releases/v6/rollback/pre-visual-polish/` in the private Kyro data bucket.

Do not merge or mark production-ready without reviewing the full implementation and completion gates.
