# AURORA / Genesis

**Version:** v0.1  
**Status:** Pre-alpha research and engineering release

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

## Public information

- [About Aurora, Genesis and Kyro](docs/architecture/SYSTEMS_PUBLIC_GUIDE.md)
- [Latest consolidation and unmerged work inventory](docs/releases/CONSOLIDATION_2026_11_07.md)
- [Public development version versus system pairing](docs/releases/VERSION_CROSSWALK.md)
- [Public website source](cloud/public-site-v1/)

## Architectural rule

> Genesis governs cognition. AURORA governs execution.

The Model cannot grant itself Engine authority. Engine-side safety, admission and operational controls remain independent of Model reasoning.

## What is public in v0.1

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

v0.1 is a **pre-alpha reference baseline**. It is suitable for research, review and contribution, but it is not presented as production-secure software.

## Repository layout

```text
.github/          GitHub templates and CI
docs/             architecture, research and governance
genesis/          public Genesis reference implementation
specifications/   public contracts and interface specifications
tests/            verification and regression tests
examples/         usage examples
rfcs/             architecture-change proposals
tools/            development utilities
```

## Installable knowledge modules (experimental)

Genesis now has a **data-only reference-pack prototype**. You can explicitly install, search, disable, replace or uninstall subject packs without changing its core weights. See [Knowledge Modules](docs/architecture/KNOWLEDGE_MODULES.md) and the [Physics Foundations demo](examples/modules/physics-foundations.json). This is **not** a degree, verified expertise, paid marketplace, or production entitlement system.

## Free language packs

The knowledge-module system also includes two **free** starter language packs: [Spanish basics](examples/modules/spanish-basics.json) and [te reo Māori basics](examples/modules/te-reo-maori-basics.json). They are installable, removable, and searchable like physics references, with Unicode-aware retrieval and explicit language metadata. They are short demonstrations, **not** complete translation models or a public Kyro marketplace.

## Experimental hierarchical memory (opt-in)

The [Genesis memory-network prototype](docs/architecture/GENESIS_MEMORY_NETWORK_RFC_2026_11_07.md) provides consent-scoped transient, working, short-term and long-term typed memory with associative links, bounded FTS5 retrieval, and an optional loopback-only Ollama embedding adapter enabled using `GENESIS_MEMORY_ENCODER=ollama` (model defaults to `embeddinggemma` if the operator has already installed it). It does **not** train model weights, automatically enable persistence for user profiles, or expose a production memory API. It remains pre-alpha and requires review/testing before deployment.

## Contributing

Start with `CONTRIBUTING.md`. Architectural changes require an RFC. Contributions should preserve the Engine/Model authority boundary unless an RFC demonstrates a concrete defect in it.

## Versioning

The first public development line is **v0.1**. Earlier internal development labels are intentionally omitted from the public repository.

## License

Public code in this repository is licensed under the **Apache License 2.0**. See `LICENSE`.
