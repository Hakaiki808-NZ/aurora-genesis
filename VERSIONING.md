# Public source versioning

**Current repository source milestone: v0.2.0-preview.1 (8 November 2026).**

This is an auditable **development-source preview**, not a GitHub Release, a general-public beta, an Aurora Engine certification, or an authority to deploy. The historical v0.1 pre-alpha baseline is retained in Git history.

## Version classes

- `VERSION`: public source-tree milestone, separate from Aurora and Genesis product identity.
- `v0.x.y-preview.n`: reviewable, incomplete development snapshots; higher numbers do **not** imply additional security assurance.
- Official release tags and GitHub Releases: created only after tests, security review, build provenance and a signed go/no-go decision.
- Build identifiers and CI run numbers: metadata, not model or Engine versions.

Changes to public APIs/contracts need compatibility tests and a reviewed migration plan. Changes to protected Aurora source happen privately; do not commit it here to simplify versioning.

## System-pairing architecture (unchanged)

The Engine/Model architectural pairing remains **Aurora V1.02 + Genesis V1.02 = V1.02.102**. It is a separate system identity and does **not** assert that a complete production-qualified V1.02 Engine or Genesis model is present in this repository or deployment. The Kyro UI has its own build identifiers.

See [version crosswalk](docs/releases/VERSION_CROSSWALK.md) and [project status](docs/governance/PROJECT_STATUS.md).

## Promotion criteria

A beta or production designation requires **evidence**, not a changed version string: authenticated real-browser Kyro acceptance, verified neural-model quality, tenant privacy controls, incident/rollback exercises, scoped Aurora security qualification, reproducible CI and a deliberate release approval. Until these gates pass, **public beta and privileged Aurora release remain HOLD**.

Security-sensitive qualification evidence and release assessments are retained outside the public repository.
