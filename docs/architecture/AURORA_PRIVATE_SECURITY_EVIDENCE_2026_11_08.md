# Aurora — Independent Admission, Angel Integrity, and Runtime Isolation Evidence

**Date:** 8 November 2026 (NZDT)  
**Environment:** AWS Sydney (`ap-southeast-2`)  
**Security classification:** public architecture/evidence summary; protected Engine implementation source remains private.

## Production private-alpha security change

The live Aurora Engine control plane now includes a separate Engine-owned Admission Lambda, without a public route. The flow is:

`Kyro/Genesis request -> JWT-protected Controller -> Engine Admission -> Engine-owned Angel -> Motor`.

Aurora independently checks session ownership, Engine epoch, execution-tier policy, action schema, Angel verdict and digest, and a DynamoDB conditional one-use request lock before C1 dispatch. Controller still provides receipt/audit commits and replay returns; Admission does not issue arbitrary Engine authority. **C4/C5, irreversible and external-side-effect execution remain prohibited.**

### Enforced IAM boundaries

- Controller's only Lambda Invoke permission is the private Engine Admission service.
- Engine Admission can invoke only Motor and Angel.
- Supervisor can invoke only a harmless Angel policy probe; it cannot directly invoke Motor.
- Motor and Angel execution roles have no Lambda invocation privileges.
- Private Engine functions expose no Lambda Function URL.
- The Aurora API route remains protected by JWT authorization.

## Live AWS verification performed

- Seven malformed/privileged/cross-actor/stale-token requests were rejected by private Engine Admission.
- A valid C1 checksum was admitted; the request ID was durably locked; direct replay was rejected.
- Six Controller integration cases passed: create session, execute C1 operation, replay existing receipt, reject C4, close session, deny post-close execution.
- Four **concurrent identical C1 requests** produced precisely one admission and three denials; request lock existed and Gate did not forge a Controller audit receipt.
- All eleven inspected operational/IAM/API configuration checks passed in the 8 November protected AWS audit.
- The supervisor now monitors Controller, Engine Admission, Angel and Motor; all were healthy at last verification.

### Software identity pinning — verified, not hardware attestation

Engine Admission independently checks AWS control-plane `CodeSha256`, IAM Role, active state, and successful update status for the exact Motor and Angel deployments before dispatch.

An isolated live fault-test Lambda using an intentionally *incorrect* pinned Angel code hash denied execution **before creating an admission lock**. The test stack was deleted after completion. The normal code-pinned C1 path was also exercised successfully.

**This is an authenticated AWS software-code-identity check, not a TPM quote, enclave attestation, measured boot, physical hardware verification or independent proof that an Engine-owned Angel cannot be subverted.**

## Runtime isolation

The live deployment places Controller, Admission, Angel and Motor in separate AWS Lambda functions with distinct IAM roles. The Linux cgroup-v2 systemd adapter is implemented as a standalone C1-only reference, not the live Engine scheduling runtime.

The GitHub workflow `.github/workflows/aurora-isolation-live-qualification.yml` attempts real Linux cgroup-limited service execution and an enforced runtime deadline on a GitHub-hosted Ubuntu runner. Its CI result must be checked; **passing a runner test does not qualify an actual Aurora production host**. No privileged Ubuntu/KVM/TEE instance was spun up in the AWS account.

## Hardware-rooted Angel attestation — unresolved release blocker

Only the existing Windows `t3.small` AWS instance was found; it was not repurposed. No live Nitro Enclave or NitroTPM quote tied to an enrolled Angel has been observed.

The required qualification is a verifier with a pinned, authenticated hardware root of trust, a fresh Engine-originating nonce, verified certificate and document signature, exact release/worker identity and approved PCR measurements, time limits, epoch/session binding and replay prevention. Reject missing, expired, changed or untrusted evidence; do not accept self-asserted software attestations.

AWS documents:
- [Nitro Enclaves trust-root and document validation](https://docs.aws.amazon.com/enclaves/latest/user/verify-root.html)
- [EC2 NitroTPM instance attestation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/nitrotpm-attestation.html)

## Release and qualification boundary

These changes improve the existing private C1 Engine implementation, **not** full protected Engine V1 certification. Production kernel/microVM isolation, actual hardware-backed Angel attestation, privileged C4/C5 Engine enforcement, independent penetration testing, continuous soak, alarm operator destination and durable recovery policy remain outstanding.

Private implementation templates and sanitized qualification results were encrypted and archived in the project's versioned, non-public AWS S3 artifact bucket.

**Release decision: HOLD.** The Controller-to-Motor IAM separation and C1 admission checks are evidence of a narrower, more defensible Engine boundary, not proof that all public-release gates have been met.

See [Aurora completion tracker #62](https://github.com/Hakaiki808-NZ/aurora-genesis/issues/62).
