# AURORA / Genesis

**Version:** v0.2.0-preview.1  
**Status:** Development source preview — public beta and privileged Aurora release **HOLD**

AURORA / Genesis is an experimental AI systems project built around a strict separation of responsibilities:

- **AURORA** — execution/runtime authority.
- **Genesis** — cognition, reasoning, planning, memory and semantic authorization.
- **Kyro** — interface/embodiment layer (separate from Engine and Model).

The public repository is intended for research, testing, interoperability work and community contribution. It does **not** claim production readiness or machine consciousness.

## Kyro: build together. Grow with knowledge.

The [Kyro launch-site candidate](cloud/kyro-launch/) showcases our two immediate differentiators: **free installable Genesis reference packs** and **role-based project collaboration** in the invite-only Kyro private-alpha workspace. Explore the [read-only workspace preview](https://d3j65cc3p66kzr.cloudfront.net/v3/preview.html#collab), the [free language and physics pack examples](examples/modules/), and [honest campaign messaging](docs/marketing/KYRO_CAMPAIGN.md).

**Deployment note (7 November 2026):** Static research/pre-alpha website assets are present in AWS CloudFront/S3 at [public site](https://d3j65cc3p66kzr.cloudfront.net/site/index.html) and [discovery preview](https://d3j65cc3p66kzr.cloudfront.net/discover/index.html). This does **not** approve public onboarding or establish browser usability. Self-service cloud installs, purchases, real-time co-editing and public access to the private workspace are not offered. See [the systems guide](docs/architecture/SYSTEMS_PUBLIC_GUIDE.md) and [release gate](docs/releases/PUBLIC_BETA_GATE_2026_11_07.md).

## Free prelaunch and community

The project is gathering **public developer feedback and voluntary early interest**, not opening unrestricted Kyro accounts. See the [free prelaunch plan](docs/marketing/FREE_PRELAUNCH_PLAN_2026_11_07.md), [prepared public posts](docs/marketing/POSTS_READY_FOR_REVIEW.md), and [GitHub-based interest form](https://github.com/Hakaiki808-NZ/aurora-genesis/issues/new?template=early-access-interest.yml). GitHub issues are public: do not post personal contact details or secrets. The site remains `noindex` pending readiness review.

## 8 November 2026: public-source security hardening

This source milestone adds a tracked-file private-boundary/credential guard, standalone self-tests, and a GitHub Actions check. The [exposure audit](docs/releases/PUBLIC_REPOSITORY_AUDIT_2026_11_08.md) distinguishes confirmed findings, incomplete scans, and actions requiring private operators. The scan cannot establish that Git history or old public artifacts are safe.

The current public repo is **not** a repository for private Aurora Engine implementations or operational secret material. See [security policy](SECURITY.md) and [public/private boundary](PUBLIC_PRIVATE_BOUNDARY.md).

Run locally with `python3 tools/check_public_boundary.py --self-test` followed by `python3 tools/check_public_boundary.py`. A pass does not certify production readiness.

## Public information

- [About Aurora, Genesis and Kyro](docs/architecture/SYSTEMS_PUBLIC_GUIDE.md)
- [Historical consolidation and unmerged work inventory](docs/releases/CONSOLIDATION_2026_11_07.md)
- [7 November GitHub repository audit (historical snapshot)](docs/releases/GITHUB_REPO_AUDIT_2026_11_07.md)
- [Current authoritative project status](docs/governance/PROJECT_STATUS.md)
- [Genesis Common AI Baseline 1.0 (GCAB-1)](docs/standards/GENESIS_COMMON_AI_BASELINE_V1.md)
- [Public development version versus system pairing](docs/releases/VERSION_CROSSWALK.md)
- [Public website source](cloud/public-site-v1/)

## Architectural rule

> Genesis governs cognition. AURORA governs execution.

The Model cannot grant itself Engine authority. Engine-side safety, admission and operational controls remain independent of Model reasoning.

## Historical GitHub consolidation (7 November 2026)

Merged PRs [#41](https://github.com/Hakaiki808-NZ/aurora-genesis/pull/41), [#37](https://github.com/Hakaiki808-NZ/aurora-genesis/pull/37), and [#43](https://github.com/Hakaiki808-NZ/aurora-genesis/pull/43) preserve a tested add-on reference, disabled neural gateway source, and evidence-based GCAB-1 standard. Follow-up merges [#45](https://github.com/Hakaiki808-NZ/aurora-genesis/pull/45) and [#46](https://github.com/Hakaiki808-NZ/aurora-genesis/pull/46) consolidate the entire repository and repair a fallback intent-context bug. The default neural inference path has **not** been enabled, Aurora cloud execution remains restricted, and public beta is **on hold**. The top unresolved blockers are [real Genesis model evaluation](https://github.com/Hakaiki808-NZ/aurora-genesis/issues/44) and [real-browser authenticated Kyro acceptance](https://github.com/Hakaiki808-NZ/aurora-genesis/issues/30). See the [full repository audit](docs/releases/GITHUB_REPO_AUDIT_2026_11_07.md) for retained draft branches and release policy.

## What is public in v0.2.0-preview.1

- Genesis reference implementation
- public architecture documentation
- Model constitution and public API
- public contracts/specifications
- tests and verification harnesses
- RFC process
- research material
- contributor documentation

## What is intentionally not public

Security-critical AURORA implementation internals, private signing material, protected recovery internals, containment internals and other operational mechanisms whose disclosure would weaken the trust boundary are excluded from this repository.

## Maturity

v0.2.0-preview.1 is an **unreleased research-source preview**; it has not passed production or public beta acceptance. It is suitable for research, review and contribution, but it is not presented as production-secure software.

## Repository layout

```text
.github/          public templates and CI guards
cloud/            public cloud templates and static site source
config/           reference model/identity metadata (no credentials)
deploy/           self-hosted reference deployment templates
docs/             architecture, research, evidence and governance
genesis/          public reference Model code
tests/            regression and qualification harnesses
examples/         data-only sample knowledge modules
rfcs/             architecture proposals
tools/            public, non-privileged development utilities
web/              Kyro frontend source
```

## Installable knowledge modules (experimental)

Genesis now has a **data-only reference-pack prototype**. You can explicitly install, search, disable, replace or uninstall subject packs without changing its core weights. See [Knowledge Modules](docs/architecture/KNOWLEDGE_MODULES.md) and the [Physics Foundations demo](examples/modules/physics-foundations.json). This is **not** a degree, verified expertise, paid marketplace, or production entitlement system.

## Protected Core and university curriculum add-ons (experimental reference)

A Genesis add-on layer is under development: a built-in, non-uninstallable
**Genesis Core**, plus optional reference packs and university-level
**sample curricula**. The starter examples map Physics and Computer Science
topics to year/unit/chapter outlines; installation can change the reference
material retrieved on the next response, but it does **not** confer a degree,
demonstrate specialist competence, or modify neural weights. See
[Genesis Add-ons](docs/architecture/GENESIS_ADDONS.md) and the
[reference catalogue](examples/addons/catalog.json).

## Neurol neural core (experimental)

Neurol v0.1 is a small, original Genesis-side recurrent neural core trained
from random initialization. It provides a UTF-8 byte tokenizer, reset-before
GRU, backpropagation through time, Adam optimization, held-out evaluation,
JSON-only checkpoints, and an opt-in text-generation backend. It has no tool
or Aurora execution authority, does not train during chat, and is disabled by
default.

Install its optional CPU dependency and run the bounded demonstration:

```bash
python -m pip install -r genesis/neurol/requirements.txt
python -m genesis.neurol.train train \
  --dataset examples/neurol/corpus.json \
  --output artifacts/neurol/candidate.json \
  --report artifacts/neurol/evaluation.json \
  --steps 600
```

For a larger, *untrained* Neurol research checkpoint with 1,026,126
parameters (999,996 additional parameters versus the default 26,130), run:

```bash
python -m genesis.neurol.train initialize \
  --profile million \
  --output artifacts/neurol/million-untrained.json
```

This uses a 216-dimensional byte embedding and 437-dimensional hidden state.
Its initialized random weights do **not** confer language capability. To train
this larger profile explicitly, use the `train` command with
`--profile million` and a properly reviewed/licensed corpus; allow for
substantially more CPU time and RAM than the prototype. The checkpoint is not
committed to this public repository. The digest-pinned, JSON-only checkpoint
remains subject to loading limits and the existing experimental gate.
An untrained checkpoint is intentionally rejected by `NeurolBackend`.

For faster *opt-in* CPU training at the expanded scale, install PyTorch
separately (`python -m pip install torch`) and use the accelerated trainer.
Its reset-before GRU implementation preserves the original parameter shapes,
and checkpoint serialization remains JSON-only:

```bash
python -m genesis.neurol.torch_train \
  --dataset examples/neurol/corpus.json \
  --initialized artifacts/neurol/million-untrained.json \
  --expected-sha256 <independently-verified-initial-sha256> \
  --output artifacts/neurol/million-trained.json \
  --report artifacts/neurol/million-report.json \
  --steps 600 --batch-size 8 --sequence-length 48 \
  --rate 0.002 --eval-every 40 --patience 5
```

A local research run selected the step-200 checkpoint by held-out validation
(best loss **1.8089**, one-time test loss **1.5490** versus unigram **3.0834**).
Further steps overfit this tiny dataset. These trained weights are **not** a
fluent language model or a deployed service. The [measured research report](
docs/research/NEUROL_MILLION_TRAINING_2026_11_08.md) explains limitations,
checkpoint provenance and independent NumPy verification. The experimental
trillion-parameter capacity planner remains design-only; it has no trained
trillion-parameter weights.

Activation requires all four explicit settings: `GENESIS_GENERATOR=neurol`,
`GENESIS_NEUROL_ENABLE=1`, `GENESIS_NEUROL_CHECKPOINT` and the independently
pinned `GENESIS_NEUROL_SHA256`. See the [design RFC](rfcs/0001-neurol.md) and
[first evaluation](docs/research/NEUROL_V0_1_EVALUATION_2026_11_08.md).

## Free language packs

The knowledge-module system also includes two **free** starter language packs: [Spanish basics](examples/modules/spanish-basics.json) and [te reo Māori basics](examples/modules/te-reo-maori-basics.json). They are installable, removable, and searchable like physics references, with Unicode-aware retrieval and explicit language metadata. They are short demonstrations, **not** complete translation models or a public Kyro marketplace.

## Contributing

Start with `CONTRIBUTING.md`. Architectural changes require an RFC. Contributions should preserve the Engine/Model authority boundary unless an RFC demonstrates a concrete defect in it.

## Versioning

The current public source milestone is **v0.2.0-preview.1**. The historical **v0.1** pre-alpha baseline remains distinct from Aurora and Genesis system identity. No GitHub release/tag or public deployment approval is implied.

## License

Public code in this repository is licensed under the **Apache License 2.0**. See `LICENSE`.
