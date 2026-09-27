# GitHub Preparation Report

Prepared as a **non-published** repository candidate.

## Applied

- public version normalized to **v0.1**
- changelogs omitted
- historical internal release labels omitted from public-facing material
- public/private boundary documented
- security-critical AURORA implementation excluded
- contributor documentation added
- RFC process added
- GitHub issue / PR templates added
- CI test workflow drafted
- research framing added
- caches, logs, lineage and generated release-history artifacts removed
- basic secret scan performed

## Remaining publication gate

1. Configure a private vulnerability-reporting channel and insert it into `SECURITY.md`.
2. Create the GitHub repository and push this package.
3. Run CI from a clean GitHub checkout before announcing it publicly.

## Automated preparation checks

- obvious secret-pattern hits: 0
- old V1.01/V1.02 labels remaining: 0


## License decision

Apache License 2.0 selected for the public repository. DCO-style contribution sign-off added.
