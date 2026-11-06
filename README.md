# AURORA / Genesis

**Version:** v0.1  
**Status:** Pre-alpha research and engineering release

AURORA / Genesis is an experimental AI systems project built around a strict separation of responsibilities:

- **AURORA** — execution/runtime authority.
- **Genesis** — cognition, reasoning, planning, memory and semantic authorization.
- **Kyro** — interface/embodiment layer (separate from Engine and Model).

The public repository is intended for research, testing, interoperability work and community contribution. It does **not** claim production readiness or machine consciousness.

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

## Contributing

Start with `CONTRIBUTING.md`. Architectural changes require an RFC. Contributions should preserve the Engine/Model authority boundary unless an RFC demonstrates a concrete defect in it.

## Versioning

The first public development line is **v0.1**. Earlier internal development labels are intentionally omitted from the public repository.

## License

Public code in this repository is licensed under the **Apache License 2.0**. See `LICENSE`.
