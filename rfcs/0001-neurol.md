# RFC 0001: Neurol v0.1 experimental neural core

Status: Implemented research candidate
Date: 8 November 2026

## Problem

Genesis can call pretrained or externally hosted neural models, but the
project needs a reproducible neural implementation that it owns and can train
from random initialization. The first version must run on a CPU, prove that
its gradients and checkpoint path work, and preserve the Genesis/Aurora/Kyro
authority boundary.

## Decision

Add Neurol under `genesis/neurol` as an optional research subsystem:

- UTF-8 byte tokens plus beginning/end boundary tokens;
- one reset-before gated recurrent unit (GRU);
- exact backpropagation through time with clipped Adam updates;
- explicit train, validation and test splits;
- reviewed, training-authorized, source-labelled corpus records;
- JSON-only checkpoints with a canonical SHA-256 digest;
- an opt-in implementation of the existing text-only generator interface.

The GRU is an established architecture. The implementation and its initial
weights are project-owned; this RFC does not claim a new neural algorithm.

## Boundaries

Neurol belongs to Genesis and returns text only. Its output remains untrusted
model material. It cannot invoke tools, create Model Authorization Proofs,
issue Aurora receipts, alter Guardians, or grant capabilities. Training is an
explicit offline command and never consumes conversations automatically.

Kyro may read `/neural/status`. Aurora retains independent admission,
execution, isolation and resource authority.

## Activation

Neurol remains disabled unless the operator explicitly selects it, enables
it, supplies a checkpoint path, and pins the checkpoint digest. The candidate
must also contain a passed learning check. A checksum detects accidental or
unapproved change when compared with the pinned value; it is not a digital
signature or a safety certification.

## Evidence required for v0.1

- analytical gradients agree with finite-difference checks;
- a controlled sequence can be learned;
- training is deterministic for a fixed seed;
- checkpoint load/save round-trips exactly and rejects tampering or shape
  changes;
- held-out loss beats the declared baseline;
- arbitrary neural text cannot become a tool call or Engine request;
- existing deterministic Genesis answers continue working with Neurol enabled
  and disabled.

## Limits and next gate

The bundled corpus is synthetic and tiny. Passing it proves the implementation
learns that corpus; it does not prove general reasoning, fluent conversation,
semantic safety or production readiness. A future version needs a licensed,
larger corpus, stronger leakage detection, task evaluations, scaling tests and
independent safety review before any default activation proposal.
