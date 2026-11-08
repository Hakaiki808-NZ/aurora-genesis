# Neurol sparse MoE trained pilot — 8 November 2026

## Scope

This is an **implemented and trained small experimental sparse-MoE pilot** for
future Neurol scaling, **not** a trillion-parameter model or production backend.

The separate opt-in module `genesis/neurol/moe_pilot.py` implements a
64-dimensional embedding, 64-dimensional GRU, top-2 learned router, four
independent 64 → 128 → 64 feed-forward experts and a byte-vocabulary output.
Unlike the design-only trillion-capacity planner, each token actually visits
only its selected two experts. Autograd updates router and expert parameters.

## Reproducible CPU experiment

| Metric | Result |
| --- | ---: |
| Model parameters | 124,934 |
| Experts | 4 |
| Activated experts per token | 2 |
| Initial validation cross-entropy | 5.6857 |
| Best validation cross-entropy | 1.6560 |
| Selected checkpoint at step | 150 |
| Early stop after | 275 |
| Test cross-entropy | 1.5305 |
| Test unigram baseline | 3.0834 |
| Test split expert token assignments | [264, 207, 213, 242] |
| Training time on CPU | 2.63 seconds |
| Cloud spend | $0 |
| Trained SafeTensors checkpoint SHA-256 | `cc593a2c0d65a82cce07af96fee8091d029d8dfbfbe0ae95d81f9f626b25509a` |

The research input is the same 40/8/8 synthetic corpus used in the Neurol
GRU experiment (SHA-256
`c21cb0aa048b3553da95b21701291d6d800e1e93cc261c9afeb09bfd70a41541`).
The checkpoint was saved using SafeTensors, reopened, and compared tensor-by-tensor
against the best in-memory checkpoint. A second independent run with the same
seed and settings produced **the same checkpoint SHA-256**, validating local
deterministic reproducibility.

## How to reproduce

```bash
python -m pip install -r genesis/neurol/requirements.txt torch safetensors
python -m genesis.neurol.moe_pilot \
    --dataset examples/neurol/corpus.json \
    --output artifacts/neurol/moe-pilot.safetensors \
    --report artifacts/neurol/moe-pilot-report.json \
    --steps 300
python -m tests.neurol_moe
```

## Boundaries and decision

- **Sufficient for:** demonstrating real differentiable top-2 sparse expert
  selection, learning and checkpoint reproducibility in a bounded CPU experiment.
- **Not sufficient for:** human-language conversation, broadly transferable
  knowledge, task reasoning, multi-device serving, distributed training,
  production safety or default activation.
- Evaluation reused an existing tiny test set across experimental architectures.
  These comparisons are exploratory, not a fresh unbiased benchmark.
- The pilot is not connected to Aurora execution and is not a standard Genesis
  inference backend. It has no access to private chat data.
- A full trillion-parameter sparse model would require orders of magnitude more
  data, hardware, expert-parallel routing, optimizer sharding and evaluation.

Next gate: train on a substantially larger licensed corpus with new reserved test
sets and test expert specialization, generalization, memory, latency and safety
before considering a user-facing activation.
