# Neurol million-parameter CPU experiment — 8 November 2026

## Evidence and status

**Experimental research candidate only. Not publicly deployed or a general conversation model.**
Neurol has an initialized GRU profile with 1,026,126 trainable parameters (exactly
999,996 more than the 26,130-parameter baseline). The model retains the reset-before
GRU, byte-level vocabulary and output-only/no-Aurora-authority boundaries.

The research run started with random, project-generated weights and used 40 approved
synthetic training documents, 8 validation documents and 8 test documents from
`examples/neurol/corpus.json` (SHA-256:
`c21cb0aa048b3553da95b21701291d6d800e1e93cc261c9afeb09bfd70a41541`).

The local PyTorch CPU training harness (which implements the reference recurrence)
was run for a maximum of 600 steps, batch 8, unroll length 48, learning rate 0.002,
validation interval 40 and early-stopping patience 5.

| Metric | Observed |
| --- | ---: |
| Parameters | 1,026,126 |
| Initial validation cross-entropy | 5.5530 |
| Best validation cross-entropy | 1.8089 |
| Best checkpoint at step | 200 |
| Training ended after early stop | 400 |
| Final selected checkpoint test cross-entropy | 1.5490 |
| Held-out unigram baseline | 3.0834 |
| CPU training elapsed | 28.567 seconds |
| Cloud expenditure | $0 |
| Checkpoint SHA-256 | `4708fc7c8e311ba96bd5d94bf45d0ab97f9a34b941ba07d2d774c1f7f234cbf3` |

**Independent verification:** A separate NumPy implementation re-opened the serialized
trained checkpoint, verified its digest, shapes, finite weights and the exact parameter
count; its measured validation loss was 1.8088738021 and test loss was 1.5489733702.
These agree with the PyTorch report within 0.0002.

## Limitations / sufficiency boundary

The model learned statistical text structure on a tiny, repetitive, synthetic corpus.
Selected greedy completions remain partially incoherent. Training became overfit after
step 200, so **increasing step count further was not justified** on this dataset.
The experimental learning check passed, but no general instruction-following,
reasoning, fluent language, multilingual ability, safety or production capability is
demonstrated. The small test set was inspected during experimentation, so it must not
be presented as a pristine, independently unobserved benchmark for future iterations.

The 1.237-trillion-parameter MoE capacity plan is **design-only**. This experiment
does not allocate or train any trillion-parameter weights.

## Reproduction / security boundaries

Use an optional CPU PyTorch environment:

```bash
python -m pip install -r genesis/neurol/requirements.txt torch
python -m genesis.neurol.train initialize --profile million \
    --output artifacts/neurol/million-untrained.json
# Independently verify and pin the initialization digest before training:
python -m genesis.neurol.torch_train \
    --dataset examples/neurol/corpus.json \
    --initialized artifacts/neurol/million-untrained.json \
    --expected-sha256 <the-verified-initialized-checkpoint-digest> \
    --output artifacts/neurol/million-trained.json \
    --report artifacts/neurol/million-report.json \
    --steps 600 --batch-size 8 --sequence-length 48 \
    --rate 0.002 --eval-every 40 --patience 5
```

The generated JSON checkpoint contains project-generated statistical weights, not
private data. It stays outside the public repository. The candidate is not activated
automatically: the Genesis backend still requires its independent opt-in and pinned
trained-checkpoint digest; neural text never directly creates Aurora actions.
