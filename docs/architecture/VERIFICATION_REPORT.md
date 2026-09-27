# Aurora v0.1 Verification Report

## Result

**PASS** for the finalized reference hardening implementation.

| Suite | Result |
|---|---:|
| Core Generation-1 Engine regression | 38/38 PASS |
| Real Genesis v0.1 cross-system integration | 4/4 PASS |
| Angel/MAP hardening | 50/50 PASS |
| Randomized protected MAP mutations | 20,000 / zero unauthorized acceptances |
| Genesis v0.1 complete Model verification after integration | PASS |

## Core coverage

The 38 core checks cover Engine boot/state legality, session epochs, Workload Capability Manifest compatibility, Gearbox resource/safety-floor behavior, Timing separation, Motor-only execution and idempotency, independent Engine grants/revocation, SETP/Situation Room authentication/anti-replay/identity binding/semantic rejection/pre-emption, sanitized Alpha beacons, service recovery, update anti-rollback, Supreme finite authority, realignment verification/timeout, session cleanup and audit integrity.

## Cross-system coverage

The actual Genesis v0.1 reference `EngineBoundary`, `IntentCapsule` and Constitution hash were loaded. The test proved a real Genesis C4 external action obtains a MAP and Aurora accepts it when all independent Engine requirements are satisfied; Genesis validates the authoritative Aurora receipt; ordinary Genesis C3 mutation remains compatible without a MAP.

## Hardening coverage

The hardening checks cover live Linux namespace Angel isolation, process separation and `no_new_privs`, worker-image pin and Engine certificate, POF authority/schema/hash chain, MAP signature/digest/release/Constitution/version/expiry/replay validation, independent Engine grant enforcement, Angel interlock/impersonation/replay/action binding, selective FAST/ELEVATED/CRITICAL failure behavior, C3/C4 compatibility boundary, randomized MAP mutations, hardware probe/fail-closed, strong-isolation-required fail-closed and optional Ed25519 MAP mode.

## Environment qualification

The release environment successfully exercised the strong Linux namespace Angel backend. It did **not** expose a usable physical TPM, KVM, SGX or SEV device. Therefore software Ed25519 was the tested Engine-key provider and no physical hardware-backed/enclave validation is claimed.
