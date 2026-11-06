# Kyro launch-site candidate — modules + collaboration

This is a **new, deployment-ready static-site source candidate**, not the already deployed CloudFront/S3 public-edge snapshot in cloud/public-beta-web/.

## Headline and customer story

**Build together. Grow with knowledge.**

Two differentiators lead the page:
1. Project collaboration: existing private-alpha V3 project roles, one-use invitations, discussions and shared versioned files. No claim of simultaneous real-time co-editing.
2. Free, expandable knowledge: Genesis has versioned open-source reference modules and short Spanish, te reo Māori and physics examples. They are not installed in customer cloud accounts. No checkout, credential claims, or paid marketplace yet.

The homepage deliberately uses "Explore", "Preview", and "View pack source" instead of fake install, buy, or public signup CTAs. It links to the existing AWS-hosted **read-only** preview and public GitHub sources. No backend keys, sign-in flow, analytics, tracking pixels, cookies, or payments occur here.

## Local preview

From the repository root:

    cd cloud/kyro-launch
    python -m http.server 8080

Open http://localhost:8080/ . The catalogue is loaded from ./catalog.json and filters without network login or private data. Its pack links point to the publicly visible module source.

For validation:

    python -m tests.kyro_marketing
    python verify.py

## Site deployment — NOT performed by this change

The beta release gate in docs/releases/PUBLIC_BETA_GATE_2026_11_07.md is currently HOLD for public onboarding. The existing 2026-11-07 public-beta-web directory is an immutable evidence snapshot of S3 objects. **Do not overwrite that snapshot or alter its original ETags as if a Git commit were a live AWS deployment.**

Proposed release path after review: upload this directory to a new versioned S3 prefix /discover/, with a CloudFront behaviour/correct content types and a bounded invalidation, then complete anonymous browser testing. Do not change root / or Cognito registration as part of a marketing copy release. Configure a CSP that permits self-hosted CSS/JS and external GitHub navigation (no inline JS needed). No build system or long-running server is required in production.

Before public advertising: rights and fluent-speaker review of language content, accurate product-scope review, human browser and mobile testing, incident/monitoring alert setup, privacy/terms review, explicit beta go/no-go, and a named support contact. These are existing launch blockers rather than reasons to exaggerate readiness.

## Follow-on Kyro integration

- Expose a read-only *actual* catalogue service from Genesis via authenticated, read-only Kyro API, mapped to account-specific entitlements. The current site is a static catalogue.
- Place a module panel in the authenticated V3 workspace that calls the dedicated user/entitlement backend, **not** the admin-token module endpoints.
- Add signed publisher manifests and license checks under Aurora / authoritative service control before marketplace purchases.
- For collaboration, maintain existing owner/editor/viewer server checks and test cross-account access and revocation. Real-time co-editing should be offered only after a dedicated concurrency model and user testing.

This marketing source can be reviewed and merged without spending AWS budget or changing public onboarding.
