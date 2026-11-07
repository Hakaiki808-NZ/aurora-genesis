# Kyro unified identity and social sign-in — implementation status

Date: 7 November 2026. Status: **shared AWS identity issuer configured; live browser sign-in not yet qualified**.

## Canonical login now configured

The Kyro V3 developer workspace and older root research beta now both use the invite-only Cognito user pool `kyro-dev-private-alpha`, id `ap-southeast-2_Pq71kumUV`, in ap-southeast-2.

- Workspace PKCE client: `68i1h2nqhvsjruneo12k0u3ahm`, callback `/v3/index.html`.
- Root research PKCE client: `7le2ihp8hcee5gptqjis49ovau`, callback `/`.
- Both hosted flows use `https://kyro-v4-private-179502447662.auth.ap-southeast-2.amazoncognito.com`.
- Root API Gateway `mex7yuj2j2` chat/status routes now use JWT authorizer `htt607` with the shared pool issuer and the root PKCE client's audience. Workspace API Gateway `ces52hcf3e` retains its existing V3 JWT authorizer.
- The developer sign-in gateway at `/site/dev-login.html` links to the established V3 workspace PKCE login.

This implements a common identity source and OAuth hosted-login domain across Kyro's two browser apps, **not yet a proven end-to-end SSO user journey**. A real first-login/password-change test and both JWT integrations must pass before declaring unified sign-in user-verified.

## Rollback and CloudFormation caveat

The root research client configuration, app JavaScript and index HTML were backed up in S3 under `backups/unified-sso-2026-11-07/`. The original root API JWT authorizer `tv0n9j` is retained for rollback, but is no longer attached to `GET /api/status` or `POST /api/chat`. New root authorizer is `htt607`; identity client is `7le2ihp8hcee5gptqjis49ovau`.

The root API Gateway is CloudFormation-managed. These direct authorizer and route changes may cause CloudFormation drift; codify them in the private infrastructure source before the next stack update. Backups and route IDs need a tested restore plan.

## Live endpoints

- V3 API `ces52hcf3e`: `GET /api/v3/health` (anonymous) and JWT-protected patterns `/api/v3/{proxy+}`, `/api/v3/aurora/{proxy+}`, `/api/v3/realignment/{proxy+}`, `/api/v3/capabilities/{proxy+}`.
- Research API `mex7yuj2j2`: `GET /api/status` and `POST /api/chat`, JWT-protected against shared identity pool (root client).
- Machine-readable, deliberately restricted reference: `cloud/public-site-v1/openapi.json`.
- API Gateway's wildcard routes do not prove every operation or HTTP verb is implemented.

## Social login roadmap — intentionally nonfunctional

Disabled previews appear in the site sign-in gateway and API developer reference for **Google, Microsoft and GitHub**. No external federation apps, secrets or social authorization providers have been enabled. Before enabling:
1. Register approved OAuth applications and Cognito federation providers. Keep secrets in protected AWS secret management.
2. Restrict callback/logout URIs; use authorization code + PKCE, state, nonce and issuer/audience verification.
3. Define safe account-linking policy. A matching unverified email must never merge accounts or grant authority.
4. Test per-app JWT audience, operator logging, CSRF protection, logout, revocation and user isolation.
5. Complete privacy/retention review and actual two-account browser acceptance.

## Test account and public beta gate

The V3 pool enforces 14+ characters with uppercase, lowercase, digits and symbols. Never weaken this for testing. A new user must remain in Cognito `FORCE_CHANGE_PASSWORD` until a valid first-login change completes.

Test-account creation did not complete in this deployment. Confirm the account separately before conducting login acceptance. No unrestricted public registration, elevated Engine permissions, paid training, or public beta was enabled.
