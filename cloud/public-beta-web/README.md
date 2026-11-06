# Kyro public-edge web snapshot

Public browser assets copied from the deployed Sydney AWS CloudFront S3 origin on 7 November 2026 (NZDT). The paths here match the website's public paths. They are **not** private Aurora Engine internals.

- Root `/`: authenticated Genesis research beta, using a Cognito pool configured for sign-up. Deterministic reference model; Aurora action execution not attached.
- `/v3/`: advanced Kyro workspace plus read-only preview and bounded Realignment School, using a separate invitation-only Cognito pool.
- `asset-manifest.json`: size and S3 ETag of each captured asset.
- Source control is not deployment. This snapshot should not be called security-qualified, production AGI, or a completed public-beta launch.
- Keep Engine high-consequence actions disabled until independent qualification.

Promotion prerequisites: real browser PKCE login, per-user persistence and authorization tests, verified backup/restore, incident alerts, retention/privacy terms, and independent spending stop.
