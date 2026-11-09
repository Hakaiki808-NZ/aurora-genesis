# Quantum integration research — Aurora / Genesis / Kyro
**Date:** 2026-11-07 NZDT | **Status:** research branch only, not production or physical QPU use

## Decision
Build an **optional hybrid quantum-classical subsystem**. Do not make quantum hardware part of the main Genesis conversation or neural-training path, and do not present small simulated quantum calculations as a demonstrated quantum speedup.

### Evidence matrix
| Candidate | Evidence | Action |
| --- | --- | --- |
| CPU statevector / circuit verification | Well-established classical simulation, free locally | Implement reference |
| QAOA for small Max-Cut optimisation | Heuristic, interesting but easily beaten/matched by classical baselines on toy cases | Research with fair comparisons |
| Quantum-native chemistry / materials | More credible specialist applications than ordinary text classification | Next research experiment |
| Quantum ML + neural network | PennyLane can bridge circuits with PyTorch/JAX, but no general demonstrated classical-data advantage | Isolated shadow study only |
| Quantum-enhanced memory / AGI | No validated general method | Later / Research; no marketing promise |
| Post-quantum cryptography | NIST FIPS 203/204/205 published | Independent crypto inventory and migration planning |

The 2026 systematic QML review [R5] finds that fair comparisons on classical data generally show parity at best, often classical superiority. A 2024 Nature Reviews Physics survey [R6] stresses explicit performance and resource benchmarks for optimisation.

## Architecture and trust boundaries
```text
Kyro future Quantum Lab UI (authenticated project / result viewer)
  -> Genesis problem formulation and semantic authorisation
  -> existing EngineBoundary / Model Authorization Proof for consequential actions
  -> Aurora independent admission and execution authority (future protected service)
     |-- local CPU simulator (this research implementation)
     |-- Amazon Braket LocalSimulator (optional SDK, not implemented)
     |-- AWS remote simulator (off by default)
     `-- AWS QPU (off by default, paid, organisation permission required)
  -> Aurora authoritative receipt -> Genesis interpretation -> Kyro display
```

**Critical distinction:** the implemented `ReferenceAdmission` is only a test-only host-injected object. It is **not Aurora's real security policy, isolation, Supreme Guardian, Angel or authentication**. Genesis cannot grant itself Engine permission, and no external quantum execution path is implemented. The host must validate tenant, proof, policy, quotas, circuit, region, sensitivity, costs, concurrency, retry and idempotency independently. The model must never supply its own trusted authorization claim.

## Implemented experiment
- `genesis/quantum_lab.py`: standard-library-only exact CPU statevector, H/CNOT Bell pair and one-layer Max-Cut QAOA.
- `tests/quantum_lab.py`: 7 unittest test cases covering physics expectations, benchmark constraints, seeded reproducibility, default denial, bad input and attempts to enable remote/paid execution.
- `tools/quantum_benchmark.py`: deterministic 3-, 4-, 5-, 6-qubit weighted Max-Cut fixtures, exact enumeration and deterministic greedy classical baseline.
- `verify.py` now runs the quantum tests in the repository's general verification. No default neural backend, tool registry, database schema, public API, AWS resources or live Aurora operations are changed.
- Hard caps: maximum 6 qubits, 4,096 final measurement samples, 625 QAOA grid evaluations; host may further restrict limits. For actual production the Engine must also enforce process-level CPU time and memory ceilings.

### Local benchmark observations
All four examples are trivial for conventional computers. Classical greedy and exact enumeration achieve the same optimum in each. QAOA expected scores were approximately **3.780/4**, **3.000/4**, **4.030/5** and **6.091/9** for 3, 4, 5 and 6 qubits. Parameter grid: 17 x 17 = 289 statevector evaluations; 1,024 final samples, fixed seed. QAOA probabilities of obtaining the optimum vary substantially. These results **do not** show quantum advantage or improved model training; they are correctness and methodology tests. See `docs/benchmarks/quantum_cpu_benchmark_2026_11_07.json`.

## Planned implementation workstreams

### A. Braket local SDK compatibility (Q1/Q2)
Install an optional, pinned `amazon-braket-sdk` in a research-only environment; run H/CNOT and QAOA on `LocalSimulator()`. Compare full basis probabilities with the independent CPU reference and report statistical deviations under shots. Explicitly handle bit ordering, shot sampling and error tolerances. LocalSimulator does not require paid AWS execution; no public API or cloud model changes.

### B. Aurora-owned remote adapter (Q3/Q4; NOT IMPLEMENTED)
Use typed job requests and a distinct protected Aurora worker. Require authenticated tenant / project, digest-bound Model proof when relevant, Aurora-side allowlist, bounded qubits/depth/shots, immutable task identity, approved region, maximum charge and pre-reserved budget. Expose only metadata to Supreme and sanitized results to Genesis. All remote devices off by default. Do not evaluate model-generated Python. Consider OpenQASM 3.1 for portable, **validated** circuit interchange [R8] and QIR only if compiler interoperability warrants it [R9]. Add per-job cancellation, retries, timeout and full cost ledger. Use signed/idempotent receipts using current Engine receipt semantics.

**AWS blocker verified:** the connected account can authenticate via STS, but Amazon Braket `SearchDevices` in `us-east-1` receives an explicit AWS Organizations **service control policy DENY**. Braket has no Sydney `ap-southeast-2` endpoint. This is not fixed by IAM alone; a legitimate organisation admin must independently approve any narrow exception. No attempt to bypass that policy and no paid task occurred. AWS Braket simulators, managed notebooks, Hybrid Jobs and QPUs each have different billing surfaces [R1–R3]. AWS Budgets alerts are not a true hard cost stop; implement an Engine-side gate before any billable operation.

### C. Hybrid quantum-classical model research (Later)
Use PennyLane/PyTorch to train a tiny variational quantum classifier on synthetic or freely licensed datasets with explicit seeds. Compare to a tuned MLP and SVM with same data splits, CPU/GPU time, preprocessing effort, total circuit executions, accuracy, confidence intervals, memory, noise sensitivity and inference latency. No auto-promotion of weights or use of user conversation data without consent and review.

### D. Quantum-native scientific benchmark (Later)
Use analytically solvable small-spin Hamiltonians and exact diagonalisation as ground truth, then a VQE implementation and controlled noise experiments. Promote only if the specialised workload demonstrates a verified benefit.

### E. Post-quantum cryptography (separate security track)
Inventory TLS, OAuth/JWT signing, Secrets/KMS, signed add-ons, model artifacts, backups and mobile clients. Assess supported NIST standards **FIPS 203 ML-KEM, 204 ML-DSA and 205 SLH-DSA**, with hybrid TLS migration and vendor compatibility review. Do not implement cryptography from scratch. PQC runs on ordinary classical computers; it does not require AWS Braket.

## Completion gates
- **Q0 implemented:** CPU Bell/QAOA tests, explicit classical baselines, fail-closed test admission and zero network cost.
- **Q1 pending:** CI from GitHub PR and separate review of code quality and regressions.
- **Q2 pending:** official Amazon Braket LocalSimulator parity with independent simulator.
- **Q3 pending:** actual production Aurora-side policy enforcement / security testing.
- **Q4 blocked:** AWS organisation policy, regional data-residency review, hard spend stop and explicit QPU financial approval.
- **Q5 future:** tenant-safe Kyro UI, retention/privacy/accessible research labels.

Keep the current public beta **HOLD** decision independent from these experimental additions. No privileged production Engine operations or public AI-quantum feature claims.

## Sources reviewed 7 November 2026
- [R1] [AWS Braket simulator selection](https://docs.aws.amazon.com/braket/latest/developerguide/choose-a-simulator.html)
- [R2] [Braket local and cloud simulator docs](https://docs.aws.amazon.com/braket/latest/developerguide/braket-submit-tasks-simulators.html)
- [R3] [AWS Braket pricing](https://aws.amazon.com/braket/pricing/) and [cost estimates](https://docs.aws.amazon.com/braket/latest/developerguide/braket-pricing.html)
- [R4] [PennyLane QAOA tutorial](https://pennylane.ai/demos/tutorial_qaoa_maxcut), [PennyLane ML integration](https://docs.pennylane.ai/en/stable/introduction/interfaces.html)
- [R5] [QML 2026 evidence review](https://www.sciencedirect.com/science/article/pii/S0957417426010407)
- [R6] [Nature Reviews Physics quantum optimisation review](https://www.nature.com/articles/s42254-024-00770-9)
- [R7] [NIST PQC migration](https://pages.nist.gov/nccoe-migration-post-quantum-cryptography/)
- [R8] [OpenQASM 3.1 specification](https://github.com/openqasm/openqasm)
- [R9] [QIR Alliance LLVM IR specification](https://github.com/qir-alliance/qir-spec/blob/main/specification/README.md)
