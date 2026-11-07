# Release consolidation and change inventory — 7 November 2026

## Scope and cut-off

Verified baseline: GitHub `main` at `0d5dcc579a7167c136e116b57c4413c79f62eb92`, committed **6 Nov 2026 23:54:51 UTC / 7 Nov 2026 12:54:51 NZDT** (“feat: ship Kyro seven-capability private beta with Genesis integration”). At audit time, **no newer commit existed on main** and **no published GitHub Releases existed**. This record distinguishes things **already present on main**, **unmerged branch changes**, **verified AWS state**, and **unverified/planned work**. A branch's divergence from main does *not* by itself establish that its work happened after the baseline commit.

## Already included in main at the baseline (do not double-count as new work)

- Kyro V3 web/research-beta source, collaboration primitives and reference APIs.
- Genesis public cognition/authorization references, modules, free language examples and reference training scripts.
- Public-private boundary policies, architecture tests, research and release qualification documents.
- Kyro marketing candidate and read-only preview source.
- Seven-capability private-beta source integration at the baseline commit.
- CI at the baseline: [tests — success](https://github.com/Hakaiki808-NZ/aurora-genesis/actions/runs/42314947149) and [Genesis neural adapter checks — success](https://github.com/Hakaiki808-NZ/aurora-genesis/actions/runs/42314947088).

## Identified unmerged work as of this audit

| Branch | Main comparison at audit | Scope / release choice |
| --- | --- | --- |
| `feat/kyro-public-site-20261107` | 16 ahead / 23 behind | 12-page static informational site, JS/CSS, CI tests. **Curated website-only files** into this consolidation; exclude divergent workspace-v5 history. Branch website CI passed. |
| `feat/kyro-mobile-platform-foundation-20261107` | 37 ahead / 23 behind | Mobile app/PWA foundation; **hold** until dependency, app-store, access and security review. |
| `feature/genesis-huggingface-model-import` | 13 ahead / 0 behind | HF import/backend/trainer expansion; **hold** for model license, execution and regression review. |
| `feature/genesis-huggingface-integration-20261107` | 9 ahead / 13 behind | Alternate HF backend; **hold** to reconcile competing implementation paths. |
| `feat/genesis-gated-bedrock-neural-backend-20261107` | 9 ahead / 23 behind | Bedrock neural adapter/gates; **hold** pending tests and quota/cost evidence. |
| `feat/kyro-frontend-completion-20261107` | 15 ahead / 23 behind | Kyro V5 workspace candidate; **hold** before public merge/deployment. |
| `feature/genesis-knowledge-modules-20261107` | 10 ahead / 11 behind | Much of reference prototype already represented on main; avoid duplicate cherry-picks. |
| `feature/realignment-school-20261107` | 6 ahead / 20 behind | Realignment reference partly already represented on main; review only outstanding diffs. |
| `feature/kyro-modules-collaboration-launch-20261107` | 10 ahead / 3 behind | Marketing/discovery site candidate already represented on main; no wholesale merge. |
| `release/public-beta-qualification-20261107` | 3 ahead / 15 behind | Qualification material partly in main; compare against latest gate, not a release authorization. |
| `feature/outcome-assurance-20261107` | 15 ahead / 11 behind | Outcome-assurance work partly integrated into main baseline; isolate remaining tests. |
| `chore/aurora-boundary-smoke-20261107` | 2 ahead / 21 behind | Public smoke-test tooling; restricted Aurora implementation excluded. |

This is a curated audit of important branches, not a claim that all branch commits are production-ready. No private Engine source, secrets, or training weights are copied as part of the website release.

## Verified AWS state during this consolidation

- CloudFront distribution **enabled and deployed** with S3 origin access control; public-site prefix `site/` contained 14 source assets, `discover/` 4 assets and `v3/` 22 objects including backups at inspection.
- Sydney CloudFormation included operating development stacks for Kyro V3, V4 login/backup, Genesis weight baseline/continuation and Aurora private-alpha controller. Some historical stack names remain in **ROLLBACK_COMPLETE**, which is not “everything healthy.”
- Lambda development functions and two API Gateway HTTP APIs existed.
- Existing S3/public website objects were inspected; an independent public-browser end-to-end acceptance check was **not** completed.
- AWS cost alerts are not an absolute spend cap. No paid GPU training or public self-registration is authorized by this release.

## Changes introduced by this consolidation

- Import the previously tested **public website only** into `main` via reviewed release branch.
- Publish a readable public three-system architecture guide, explain the status and known limits, and link it from the informational site.
- Add this source-of-truth change inventory, version crosswalk and release instructions.
- Keep the public repository version at **v0.1**, reserve exact system pairing **V1.02.102** for explicitly qualified architecture identity.
- Preserve both the existing `/v3/` workspace and `/discover/` preview during website publication.

## Public beta decision

**HOLD for general-public onboarding.** See `docs/releases/PUBLIC_BETA_GATE_2026_11_07.md`. The website is a research-stage information preview and does not change the private Engine authorization controls.

## Next blockers versus improvements

**Blockers:** actual user-browser login test, privacy/retention/deletion review, access isolation, alerts with working operator notification, backup/restore trial, limits and cost stop, Engine assurance, model capability evaluation.

**Later/V2/research:** mobile app-store releases, HF model weight imports and licensing, paid degree-like specialist packs, multiagent orchestration, real-time co-editing, broader autonomous execution. These must be separately tested before merging or marketing as deployed features.
