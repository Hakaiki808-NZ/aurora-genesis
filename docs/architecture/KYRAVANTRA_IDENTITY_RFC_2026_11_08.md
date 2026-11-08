# Kyravantra Identity — verified identity broker (RFC draft)

**Date:** 2026-11-08 (NZDT)
**Status:** architecture + locally tested reference; NOT deployed or government-approved.
**System position:** separate external trust service alongside Aurora (Engine), Genesis (Model) and Kyro (Interface).

## Purpose

Offer optional, consent-driven identity verification to users who need higher assurance. Existing AWS Cognito remains the account authentication system; signed provider assertions raise only a narrow verification claim. Verification never automatically grants Engine privileges, administrative permissions or expanded model access.

```
Kyro account (AWS Cognito)
   | signed account token
   v
Kyravantra Identity
   +--> NZ RealMe verified-identity assertion service [approval required]
   +--> AU accredited Digital ID provider/exchange [agreement required]
   |
   +--> encrypted, minimal verification state
   +--> future short-lived signed claims to Aurora policy
                 |
                 +--> Genesis sees only approved scoped facts, never raw PII
```

## Confirmed external constraints

**NZ RealMe:** Only the *verified-identity assertion* service is intended for approved private-sector organisations. The generic RealMe login capability is government-only. Private entities must be approved participating agencies under the Electronic Identity Verification Act 2012. RealMe's official OIDC flow supports authorisation code, `openid profile`, signed ID tokens and an assertion-only `fit` claim; ordinary login `sub` does not prove identity. RealMe provides MTS, ITE, approval and launch coordination. Register static HTTPS callback, complete co-branding/privacy terms, request only minimal claims.

**Australia:** myGov is an online government-service portal, not a general identity verification provider. myID is an Australian Digital ID credential. Accredited providers or exchanges outside AGDIS may contract with private relying parties. Private AGDIS participation is scheduled to open in December 2026 and regulator approval is required. The user should retain an inclusive alternative where government Digital ID is voluntary. Australia distinguishes identity-proofing level (IP) from authentication level (AL); provider-specific signed verified evidence must be contracted and mapped.

**NZ Trust Framework:** The Digital Identity Services Trust Framework Act 2023 and current rules provide a separate accreditation regime. Do not imply this new service is officially accredited without regulator approval.

## Security invariants

1. Account bound to Cognito cryptographically validated `sub` before starting an identity flow.
2. Always validate provider JWKS signature, issuer, audience, expiry and nonce, one-time anti-CSRF state and prescribed authentication strength.
3. Only contractually approved verified-attribute assertions count; login-only tokens or a user's own uploaded text do not.
4. Do not store ID documents, document numbers, photos, birth dates, names, OAuth tokens or raw signed assertions, and do not use any of these to train Genesis.
5. Separate per-user verification records and explicit deletion. Use purpose-scoped, expiring trust claims for Aurora, not unrestricted user profile claims.
6. Add regulator-approved consent wording, subject access/retention policy, accessibility and supported manual alternatives, third-party security test and incident response.
7. No public verification enrollment while Kyro's existing private-alpha release gate remains on HOLD.

## Implementation milestone

Runnable local FastAPI reference bundle with SQLite-only dev store, one-use OIDC callback, explicit disabled-by-default providers, Cognito-token check, pseudonymised verified evidence, account-isolated status, unlink, and synthetic tests. The reference **fails startup in production mode** until an encrypted DynamoDB-backed implementation is provided. No production AWS resources or RealMe/AGDIS credentials were changed.

Next gate: implement DynamoDB and Lambda/API Gateway behind existing Cognito controls, sign Aurora-audience assertions, verify privacy/legal obligations; obtain RealMe participating-agency approval and AU provider terms before live assertion testing.

## Official references

- https://www.realme.govt.nz/en-nz/work-with-us/
- https://developers.realme.govt.nz/how-realme-works/realme-and-oidc/oidc-token-request-and-response
- https://developers.realme.govt.nz/how-to-integrate/core-steps-for-technical-oidc-integration
- https://www.digitalidsystem.gov.au/using-digital-id-for-your-business-or-organisation
- https://www.digitalidsystem.gov.au/the-australian-government-digital-id-system-agdis
- https://www.legislation.govt.nz/act/public/2023/13/en/latest/
