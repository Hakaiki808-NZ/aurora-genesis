# Kyro public website · alpha preview (7 November 2026)

A separate public information site for the existing Kyro private-alpha workspace. Source is intentionally kept out of the restricted Aurora Engine.

## Routes

- `index.html`: landing and three-system architecture
- `blog.html`: searchable journal and article deep-links
- `developers.html`: development overview
- `dev-login.html`: gateway to existing `/v3/index.html` Cognito PKCE login (no new credentials)
- `docs.html`: searchable research and integration documentation
- `modules.html`: planned language/specialist packs with filters and detail panel
- `collaboration.html`: interactive role explorer
- `roadmap.html`: filterable milestones
- `about.html`, `status.html`, `privacy.html`, `404.html`

## Release

Upload **the directory contents** as `site/*` objects to the existing Kyro frontend S3 bucket, then invalidate CloudFront `/site/*`. Test at
https://d3j65cc3p66kzr.cloudfront.net/site/index.html

Never overwrite the existing root research beta or private `/v3/` workspace as part of this public-site rollout.

`node --check cloud/public-site-v1/site.js`
`node tests/kyro-public-site-static.cjs`

Pages are `noindex,nofollow` until reviewed for public launch. The blog uses source-controlled posts rather than a CMS; the knowledge marketplace and paid installation are not active. The privacy page is preliminary; do not treat it as final service terms. Login is invite-only and is processed only by the existing Cognito flow; no passwords or user tokens are stored here.
