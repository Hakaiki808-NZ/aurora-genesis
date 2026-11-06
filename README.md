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

## Contributing

Start with `CONTRIBUTING.md`. Architectural changes require an RFC. Contributions should preserve the Engine/Model authority boundary unless an RFC demonstrates a concrete defect in it.

## Versioning

The first public development line is **v0.1**. Earlier internal development labels are intentionally omitted from the public repository.

## License

Public code in this repository is licensed under the **Apache License 2.0**. See `LICENSE`.

## Local Kyro / Genesis research alpha

The separately authenticated, **loopback-only** Kyro alpha is started with:

```sh
python -m pip install -r requirements.txt
python launch_local_alpha.py
```

Open http://127.0.0.1:8767 and paste the access token printed in the
launch terminal. No Aurora execution engine is connected in this public
reference build. The default backend is deliberately deterministic and
limited; set `GENESIS_GENERATOR=ollama` only when opting into local Ollama.

Run `python verify.py` for the regression suite (including the local HTTP
integration test), and `python -m evals.baseline` for elementary cognitive
regression probes. **These tests do not establish AGI.**

See [launch qualification and blockers](docs/launch/ALPHA_READINESS.md).
