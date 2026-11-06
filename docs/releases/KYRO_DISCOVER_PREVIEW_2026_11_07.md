# Kyro /discover/ static marketing preview — AWS deployment record

**Date:** 7 November 2026 (NZDT)
**Source:** main commit aed0aafb41a43f9c4f0920a5a901b1f43b53add8, merged PR #27.
**Purpose:** Public, read-only promotional page for free installable Genesis knowledge references and Kyro invite-only collaboration.

**Expected URL:** https://d3j65cc3p66kzr.cloudfront.net/discover/index.html

## Actions actually performed

Reused the existing enabled Sydney CloudFront distribution `E3P0BZ3PPWYCO` and its existing S3 origin. Uploaded four new objects with conditional create-only `IfNoneMatch: *` and five-minute cache-control:

- `discover/index.html` — 8,916 bytes, text/html; charset=utf-8
- `discover/styles.css` — 11,238 bytes, text/css; charset=utf-8
- `discover/app.js` — 3,491 bytes, application/javascript; charset=utf-8
- `discover/catalog.json` — 1,619 bytes, application/json; charset=utf-8

Each new S3 object was verified using HeadObject. Bucket policy permits this CloudFront distribution to read objects beneath the bucket wildcard path, and the CloudFront distribution is enabled with its existing S3 origin.

No existing objects were overwritten. No route, authentication policy, Cognito setting, backend, budget, CDN distribution configuration or Aurora control was changed. No external advertising campaign, advertising spend, purchases, self-service installs, or sign-up flow was initiated.

## Verification limitations / release decision

- Source: `python -m tests.kyro_marketing`, full Genesis verification and Node browser syntax checks passed in GitHub PR #27.
- S3 upload and object metadata verification passed; the four deployment paths exist with expected sizes and MIME types.
- Direct anonymous HTTP verification of the CloudFront URL **could not be completed** from the available web checker (site inaccessible to checker) or container (external DNS unavailable). **Do not report an independently confirmed public-browser success yet.**
- Human device checks and the broader release gate in `docs/releases/PUBLIC_BETA_GATE_2026_11_07.md` remain outstanding. The original `cloud/public-beta-web/` deployment evidence snapshot remains unchanged.
- The landing page labels this as an early-access preview, links to existing read-only workspace preview, and avoids public signup or checkout claims.

**Recommended next acceptance test:** Open the expected URL in a normal browser, check mobile layout, switch language/knowledge filters, confirm all GitHub pack links, and confirm collaboration CTA goes to the read-only sample. Do not use broad paid advertising until beta gates and content review are closed.
