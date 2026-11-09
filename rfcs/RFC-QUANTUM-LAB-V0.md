# RFC: Optional Quantum Lab reference backend for Genesis v0.1

**Status:** Experimental review candidate. Do not merge as production security qualification.  
**Scope:** local simulation / scientific benchmark; excludes Aurora privileged internals, actual cloud quantum tasks, credential handling and Kyro production UI.

## Motivation

Offer genuine, measurable quantum research under existing Engine/Model/Interface boundaries, without claiming immediate general-AI advantage or creating a paid dependency. Preserve the public-beta HOLD release decision.

## Proposal

1. Add the dependency-free `genesis.quantum_lab` reference CPU simulator; no default tool registry registration or automatic model-weight updates.
2. Require a host-injected, explicitly enabled **test-only** `ReferenceAdmission`; otherwise fail closed. Do not describe it as production policy or cryptographic proof.
3. Implement Bell-state test and Max-Cut QAOA depth-one with deterministic grid search. Compare to exact enumeration, deterministic greedy and uniform random expectation. Report evaluation budgets and actual backend.
4. Add repeatable offline `tests.quantum_lab` and `tools.quantum_benchmark`; include test module in root `verify.py` so CI checks it.
5. Keep an independent specification and research plan for future Aurora-owned adapter, AWS Braket compatibility, post-quantum cryptography and Kyro UI; no external runtime mutation.

## Alternatives evaluated

- **Direct AWS Braket now:** rejected due to explicit organisation SCP denial and paid-task risks.
- **Embed quantum logic into Genesis main language-model inference:** rejected; no validated benefit, expands hot-path and failure/cost surface.
- **Move the Quantum Engine under Genesis Guardians:** rejected; violates Aurora execution authority.
- **Post-quantum crypto as quantum hardware job:** rejected; PQC algorithms run on conventional hardware and belong to independent security planning.

## Evidence / limitations

Local 3–6-qubit examples run in milliseconds and provide mathematically correct statevector results. Classical exact enumeration and greedy solve all benchmark fixtures. QAOA quality varies; **no quantum advantage** is demonstrated. No AWS quantum calls, no functional Kyro integration, no actual Aurora admission, and no claim of tamper-proof isolation.

## Rollback

Remove `genesis/quantum_lab.py`, `tests/quantum_lab.py`, `tools/quantum_benchmark.py`, and remove its test registration from `verify.py`. No existing database migration, API route, default tool registration or AWS service is changed.

## Acceptance

- At least 7 test cases for Bell normalization/correlation, small optimisation, malformed inputs, default denial, remote/cost denial, seed determinism and width/budget bound.
- All benchmarks emit no-QPU/no-advantage status and track classical baselines.
- All default CI remains green; independent code review before merge.
