# Kyro unified identity and social sign-in — implementation status

Date: 7 November 2026. Status: **private-alpha baseline; federation NOT enabled**.

## Canonical login

The Kyro V3 developer workspace authenticates against the invite-only AWS Cognito user pool `kyro-dev-private-alpha` in ap-southeast-2. Its hosted OAuth 2.0 authorization-code + PKCE browser client uses a CloudFront callback at `/v3/index.html`. Developer sign-in from `/site/dev-login.html` directs users to that same workspace. This shares the identity **within the developer entry path and V3 workspace**; it is not yet platform-wide unified login.

The old root research beta still uses a different Cognito pool and a separate API JWT authorizer. Migrate its browser client and authorizer to the canonical issuer only after regression testing, so existing tokens cannot be silently misinterpreted. Preserve JWT scopes, per-user isolation and fail-closed authorization. No cross-identity claims until this is complete.

## Live API verification

Cloud resources observed: V3 HTTP API `ces52hcf3e` with `GET /api/v3/health` (anonymous) and JWT-protected routes `/api/v3/{proxy+}`, `/api/v3/aurora/{proxy+}`, `/api/v3/realignment/{proxy+}`, `/api/v3/capabilities/{proxy+}`. Legacy JWT-protected research API: `mex7yuj2j2` with `GET /api/status` and `POST /api/chat`. API Gateway's wildcard route does not prove every operation is implemented. No new backend capabilities were enabled as part of this website update.

## Social login roadmap — nonfunctional by design

The UI has disabled labels for Google, Microsoft and GitHub, explicitly marked **coming soon**. Do not create active provider links until each identity provider is formally configured. Before enabling:
1. Register approved OAuth applications and Cognito federation provider connections; keep secrets only in protected AWS secret storage.
2. Scope callback / logout URIs to official Kyro domains; use hosted authorization-code + PKCE, state, nonce and issuer/audience checks.
3. Define account-linking and verified-email policy that prevents untrusted accounts being linked by matching email alone.
4. Recheck Cognito client accepted providers, JWT authorizers, CSRF, logout and revocation; document privacy and retention.
5. Complete login, failure, two-account isolation and recovery smoke tests before advertising federation.

No public self-registration is approved for the V3 workspace. No identity-provider secrets or credentials belong in the GitHub repository.

## Testing account caveat

The V3 Cognito pool requires a temporary password of at least 14 characters with uppercase, lowercase, digits and symbols. An 8-character lowercase/digit-only password must never trigger a policy downgrade. First-login password change is enforced by Cognito's `FORCE_CHANGE_PASSWORD` state only after a securely provisioned user is verified.

## Release decision

Publishing an API directory and placeholders does not clear public beta gates. Keep Aurora's high-consequence actions disabled and continue live PKCE, privacy, alarm, backup and neural-inference qualification.
