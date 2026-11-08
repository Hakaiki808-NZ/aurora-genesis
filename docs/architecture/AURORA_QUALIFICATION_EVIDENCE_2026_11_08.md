# Aurora Engine — Production Qualification Evidence (8 November 2026)

**Scope:** Aurora Engine only. This record does not authorize public release, privileged execution, or changes to Genesis/Kyro semantics.

## Verified AWS environment (Sydney, ap-southeast-2)

- `aurora-cloud-private-alpha-v1` and `aurora-private-supervisor-v1` both deployed successfully.
- The live private engine remains `READY`, with an execution tier restricted to **C1** and `critical_execution=false`.
- Controller, Motor and Angel are separate AWS Lambda functions. The supervisor performs bounded health probes and enters `SAFE_HOLD` after three failures. An isolated live failure drill verified this sequence without modifying production control state or session records.
- Five live negative admission tests passed (unknown Motor operation, protected Supreme operation, high-tier Angel request, malformed Angel action, anonymous Controller request).
- Continuous DynamoDB point-in-time recovery remains **disabled**. Do not silently enable recurring PITR billing.

## Durable ledger backup and restore — PASSED (with defined limits)

1. Created an **on-demand backup** of the actual `aurora-cloud-v1-ledger-dev` table.
2. Restored it as a separate, temporary DynamoDB table.
3. Compared all ten records by primary key and attribute content.
4. All ten primary keys and nonvolatile attributes matched. The sole difference from the *live* source after the backup was the supervisor's `checked_at` timestamp, as expected for a concurrently updated operational record.
5. Archived the qualification report in a **private encrypted versioned S3 artifact bucket**, under `aurora/private-engine/qualification/2026-11-08-ledger-restore-drill.json`.
6. Deleted the one-time backup and initiated deletion of the temporary restore table. The original table was not altered by the drill.

**Passing scope:** one-time snapshot backup/restore of the live C1 ledger. **Not proven:** continuous PITR, scheduled backups, RPO/RTO, cross-region recovery, or complete application recovery.

## Gearbox / Timing: bounded Linux host reference, NOT production qualification

A **public conformance helper**, `tools/aurora_host_c1_reference.py`, prepares a real `systemd-run` transient *service* with kernel cgroup v2 constraints:

- CPUQuota, MemoryMax, TasksMax, RuntimeMaxSec, IOWeight;
- independent unprivileged service identity, no new privileges or Linux capabilities;
- read-only system/home protection, private temp and network isolation;
- a SHA-256-pinned executable; no shell interpolation; timeouts fail closed.

The reference is **not automatically executed or installed**. The CLI exposes only a read-only host preflight. Higher tiers and privileged execution are always denied. Linux/systemd/cgroup-v2 presence, controller availability and a provisioned service account must all be verified.

**Important limits:** this is a proof-of-integration / qualification candidate, *not* the protected Aurora scheduler. IOWeight is relative and does not impose per-device hard throughput limits; the isolated unit does not by itself reserve global Engine/Angel memory safety floors. A dedicated Linux worker, isolation benchmarks, cgroup accounting readback, headroom floors, failure injection, measured jitter and a 24/7 soak are still required. Runtime deadlines do not prove deterministic real-time scheduling.

## Hardware-backed Angel attestation — NOT QUALIFIED

- The existing AWS compute instance is a Windows `t3.small`. It was not repurposed for Aurora.
- The inspected instance does **not** report an active TPM configuration. AWS instance-family support is not evidence of an actual TPM-sealed key or verified quote.
- No qualified Linux NitroTPM, physical TPM/HSM, or enclave attestation chain was presented.
- The private Engine must require **fresh challenge-bound, signed, verifier-validated hardware evidence** covering the worker identity, code measurement and runtime epoch before admitting any hardware-required Angel. Missing, stale, forged or untrusted evidence must leave privileged operations disabled.
- Do not substitute a software-generated challenge response for hardware attestation.

## Privileged execution — DENIED BY DEFAULT

- All public `SUPREME.*` and `ANGEL.*` control routes remain forbidden.
- C4/C5 and irreversible/external actions are **not enabled**. A permissive SDK-side authorization proof must never independently grant Motor execution.
- Promotion requires a protected private Engine implementing and adversarially testing independent Engine admission, Model Authorization Proof verification, Angel interlock verdict, non-replay nonce/epoch fences, least-privilege IAM, operator hold and immutable audit. These require target-specific implementation and independent review.

## Signed release provenance

- `.github/workflows/aurora-contract-provenance.yml` builds a reproducible archive of the **public Engine contracts**.
- The workflow uses GitHub's OIDC-backed `actions/attest@v4` to generate verifiable Sigstore/SLSA provenance, with no static private signing key in GitHub. Verification: `gh attestation verify <artifact> --repo Hakaiki808-NZ/aurora-genesis`.
- This workflow **does not sign or publish Aurora's protected runtime binaries**. Those need a separate pinned private release pipeline with artifact-digest verification, key custody, threshold authorization and rollback protection.
- Passing a GitHub workflow is not evidence of a signed production deployment.

## Release gate

**HOLD.** Only the on-demand database restore and restricted supervision/negative tests are validated against live AWS. The Linux host adapter is conformance-only; production resource and timing enforcement, real hardware-backed Angel attestation, C4/C5 authorization and signed *private Engine binaries* remain unqualified.

See [Aurora completion issue #62](https://github.com/Hakaiki808-NZ/aurora-genesis/issues/62).
