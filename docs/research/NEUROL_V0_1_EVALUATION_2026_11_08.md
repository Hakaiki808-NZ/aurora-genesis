# Neurol v0.1 evaluation — 8 November 2026

## Result

Neurol v0.1 passed its bounded learning and integration gate. It remains an
experimental candidate and is not qualified as a general language model or a
production Genesis backend.

## Reproducible run

| Measure | Result |
| --- | ---: |
| Architecture | byte embedding + reset-before GRU + softmax |
| Pretrained weights | no |
| Parameters | 26,130 |
| Training documents | 40 |
| Validation documents | 8 |
| Test documents | 8 |
| Training steps | 600 |
| Seed | 1907 |
| Initial validation cross-entropy | 5.5531 |
| Selected validation cross-entropy | 2.0124 |
| Held-out test cross-entropy | 1.8742 |
| Held-out unigram baseline | 3.0834 |
| CPU training time observed | 7.275 seconds |
| Cloud cost | USD 0 |
| Checkpoint round-trip | passed |
| Learning check | passed |

Corpus SHA-256:
`c21cb0aa048b3553da95b21701291d6d800e1e93cc261c9afeb09bfd70a41541`

Candidate checkpoint SHA-256:
`74121c85bddbced9eb556495940b98b74dda5a5144c3b18fbf97b2ed2945762a`

The candidate bytes are reproducible from the tracked corpus and command in
the README. They are intentionally not tracked so future private training data
cannot be accidentally published with model weights.

## Interpretation

Validation loss decreased by about 64%, and the one-time held-out test result
beat the unigram baseline. Numerical gradient checks, deterministic retraining,
checkpoint tamper/shape rejection, inference statelessness, opt-in gating and
the text-only authority boundary passed.

Greedy samples were still repetitive fragments. This means the network learned
local byte patterns but is not yet a useful conversational model. The result is
an implementation milestone, not a capability claim.

## Known limits

- The corpus contains only original synthetic architecture statements.
- Split checks catch normalized exact duplicates and shared group identifiers,
  but do not detect paraphrase or semantic leakage.
- The test set is small and should not be reused for architecture tuning.
- No broad knowledge, instruction-following, multilingual, adversarial, bias,
  privacy-memorization or long-context evaluation has been completed.
- A pinned SHA-256 checksum is integrity evidence, not signer identity.
