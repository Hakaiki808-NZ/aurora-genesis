# Changelog

This file describes the **public source tree**. It does not attest to private Aurora deployment releases or to a production-qualified Genesis model.

## 0.2.0-preview.1 — 2026-11-08 (source milestone only)

### Security and repository hygiene
- Add a standard-library, tracked-file guard that blocks common credential formats, private Engine paths and local state/secrets.
- Run the guard and self-tests in a least-privilege GitHub Actions job on pull requests and main.
- Expand .gitignore coverage for local credentials, state, private Engine code and signing material.
- Clarify vulnerability handling, incident rotation/history-remediation advice and source release gates.

### Documentation
- Make public source version distinct from the Aurora/Genesis V1.02 architectural identity.
- Correct the README's tracked-source directory listing and mark older consolidation reports as dated history.
- Add a reviewable public-exposure inventory and outstanding operator checks.

### Qualification limits
- This milestone is **not** a GitHub Release, beta launch, Engine qualification or deployment change.
- No private Engine code or credentials are intentionally added.
- No AWS infrastructure or customer accounts are modified.
- Test results and unreviewed legacy history must be checked before any release-promotion decision.

## 0.1 — initial public pre-alpha source baseline

Historical reference baseline; earlier internal development identifiers are not public release tags.
