## Problem

## Change

## Architectural impact

## Security and public exposure
- [ ] No protected Aurora Engine source, privileged operational details or internal runbooks added.
- [ ] No credentials, tokens, personal information, logs, database contents, AWS state files or private keys added (including examples and comments).
- [ ] Public browser endpoints/client IDs are intentional and protected APIs validate authorization.
- [ ] I reviewed the full diff **and** any history/branch-specific exposure for this change.
- [ ] Public-boundary CI guard passes; any flagged file was investigated without putting its secret value in logs.

## Tests and verification (link actual CI results)

## Stabilization gate (active since 2026-11-09)
- [ ] This change preserves the Kyro feature freeze, or is necessary maintenance for the Aurora/Genesis/E2E release gate.
- [ ] For Kyro UI changes: maintenance-class title, reviewed scope and the exact exception line below.

Kyro-freeze-exception: stabilization

## Release impact
- [ ] This PR does **not** silently promote source-preview work to general beta or qualified Aurora production.
- [ ] If versioning changed, CHANGELOG and release/qualification evidence explain why.

## Alternatives considered

- [ ] I preserved the Engine/Model authority boundary, or linked an approved RFC explaining the change.
- [ ] I added or updated tests where appropriate.
