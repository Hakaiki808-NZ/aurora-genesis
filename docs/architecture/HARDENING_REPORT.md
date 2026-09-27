# Aurora v0.1 — Angel / Engine Boundary Hardening Report

## Result

**PASS — v0.1 reference hardening implementation completed and regression-tested.**

Aurora remains Generation 1. The changes are compatible implementation hardening and contract extensions, so the Engine release advances from **pre-v0.1 to v0.1** without changing the Aurora release name.

## Requested items

1. **Angel Cells — COMPLETE for the reference profile.** Angels execute outside the Genesis process in separate OS processes. The tested Linux profile successfully used user, mount, PID, network, IPC, UTS and cgroup namespaces. A required-strong-isolation policy fails closed if namespaces cannot be created.
2. **Protected Observability Fabric — COMPLETE.** Engine-owned, schema constrained, append-only and hash chained. The Model has no public write/read/suppress/reorder endpoint. Semantic-field injection and unauthorized writer objects are rejected.
3. **Angel Attestation — COMPLETE.** Worker-image SHA-256 is release-pinned; each Angel creates an ephemeral Ed25519 identity, signs an Engine challenge, and receives an Engine-signed certificate binding its key, code hash, session and isolation profile.
4. **Angel Interlock Tokens — COMPLETE.** Tokens bind Angel type, session, request ID, action digest, verdict, sequence, nonce and expiry. Forgery, replay and action substitution were rejected.
5. **Aurora-side MAP verification — COMPLETE.** CRITICAL/high-consequence requests validate Genesis v0.1 proof schema, Model release, Constitution hash, capability, action digest, Model-side verdicts, time window, signature and proof replay state.
6. **Selective fail-closed — COMPLETE.** FAST loss -> DEGRADED with remaining protections verified; ELEVATED required-Angel loss -> RESTRICTED + blocked; CRITICAL required-Angel loss -> blocked.
7. **Hardware-backed key support — IMPLEMENTED, physical validation environment-limited.** TPM2-backed signing is selected only when both a TPM device and required tpm2-tools are available. `require_hardware_keys=True` fails closed otherwise. The release environment exposed no TPM/KVM/SGX/SEV device, so the executed tests used explicit software Ed25519 fallback.

## Compatibility corrections discovered during implementation

### MAP boundary

An early draft required MAPs for every ELEVATED/C3 mutation. That conflicted with Genesis v0.1, which attaches MAPs to C4/C5, external, privileged or irreversible actions. Aurora v0.1 now requires MAP at the **CRITICAL/high-consequence boundary**, preserving the established Model contract.

### Idempotency vs MAP replay

A naive one-use MAP check would reject an exact network retry after a successful Motor action, weakening the pre-v0.1 idempotency guarantee. v0.1 resolves this by caching the exact request fingerprint and authoritative receipt per `(session, epoch, request_id)`. Exact retries return the prior receipt; the same proof used under a new request ID is rejected as replay; the same request ID with changed content is rejected as a collision.

### Baseline preservation

The initial hardening-only tree did not include all Build-7 reference modules. Before release, the pre-v0.1 baseline behavior was restored/reconstructed from the canonical Engine documentation: state/session lifecycle, Motor, Gearbox/Gears/4WD, Timing, Situation Room/SETP, Alpha Beacon, Supreme finite authority, service supervision, Workload Capability Manifest, realignment, audit identity and update rollback controls. This prevented v0.1 from becoming a security overlay that silently dropped Engine functionality.

## Executed verification

- Core v0.1 regression: **38/38 PASS**.
- Dedicated v0.1 hardening: **50/50 PASS**.
- Randomized MAP protected-field mutations: **20,000 / 20,000 rejected**.
- Real Genesis v0.1 -> Aurora v0.1 integration: **4/4 PASS**.
- Genesis v0.1 complete Model verification suite: **PASS unchanged** after integration.
- Linux namespace Angel profile: **active and verified** in this environment.
- `no_new_privs` process hardening: **verified**.
- HMAC compatibility MAP and asymmetric Ed25519 MAP modes: **PASS**.
- Hardware-required/no-hardware path: **fails closed as designed**.

## Security interpretation

The seven requested mechanisms are now implemented at reference level and do not alter the founding authority model. Supreme does not gain Model semantics; Angels do not become Guardians; Genesis cannot install Engine handlers or issue Engine grants. Stronger deployment mechanisms such as microVMs/TEEs may replace the reference isolation backend without changing the Model semantic architecture or public Generation-1 contract.
