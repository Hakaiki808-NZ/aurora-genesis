# Kyro public website · alpha preview (7 November 2026)

A separate public information site for the existing Kyro private-alpha workspace. Source is intentionally kept out of the restricted Aurora Engine.

## Routes

- `index.html`: landing and three-system architecture
- `systems.html`: dedicated, accessible public systems guide (Aurora / Genesis / Kyro)
- `systems.css`: responsive guide-only light silver styling
- `blog.html`: searchable journal and article deep-links
- `developers.html`: development overview
- `dev-login.html`: gateway to existing `/v3/index.html` Cognito PKCE login (no new credentials)
- `docs.html`: searchable research and integration documentation
- `modules.html`: planned language/specialist packs with filters and detail panel
- `collaboration.html`: interactive role explorer
- `roadmap.html`: filterable milestones
- `community.html`: $0 research participation and GitHub-hosted public early-interest form (no email capture or user accounts)
- `about.html`, `status.html`, `privacy.html`, `404.html`

## Release

**AWS alignment verified 7 November 2026:** a CloudFront-backed S3 prefix `site/` already contains all 14 original website files. For incremental publication, upload only the changed objects, preserve `/v3/` and `/discover/`, and invalidate the specific updated `/site/*` paths. Test at
https://d3j65cc3p66kzr.cloudfront.net/site/index.html

Never overwrite the existing root research beta or private `/v3/` workspace as part of this public-site rollout.

`node --check cloud/public-site-v1/site.js`
`node tests/kyro-public-site-static.cjs`

Pages are `noindex,nofollow` until reviewed for public launch. No automatic Google indexing is enabled. The community interest form uses a **public GitHub Issue Form**: participants should not enter personal contact details, and it does not grant private-alpha access. The file is in `.github/ISSUE_TEMPLATE/early-access-interest.yml`. Static sources need a separate controlled S3 deployment to reach CloudFront. The blog uses source-controlled posts rather than a CMS; the knowledge marketplace and paid installation are not active. The privacy page is preliminary; do not treat it as final service terms. Login is invite-only and is processed only by the existing Cognito flow; no passwords or user tokens are stored here.
