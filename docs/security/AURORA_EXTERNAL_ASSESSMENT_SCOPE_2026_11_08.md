# Aurora Engine — Independent Security Assessment Engagement Scope

**Status:** Ready for external assessor engagement; NOT an independent audit or certification.

**System boundary:** Aurora is the closed-source Engine. Genesis is the Model and Kyro is the Interface. Neither may authorize Motor independently. Current production operation is strictly C1, `critical_execution=false`; public release stays HOLD.

## Access and handling

The assessor receives a time-limited, read-only copy of protected Aurora deployment source and exactly deployed Lambda package digests, build provenance, IAM policies, resource controls, private audit records and security test plans under a separate confidentiality agreement. Do not add Engine source, credentials, actor records, or keys to the public GitHub repository. The assessor uses a dedicated non-production qualification account and isolated canary identities, with written scope and rollback/cleanup procedures.

**No permission is granted to execute privileged C4/C5 actions, exploit real user sessions, modify production role policies, alter protected Engine state, or probe third-party systems.** Destructive/adversarial scenarios must be conducted against a dedicated disposable environment, with fail-closed controls and operator notification.

## Independent assessor required work

| Gate | Required experiment and evidence | Passing condition |
|---|---|---|
| Trust roots and chain | Independently verify AWS Nitro attestation root, document certificate path, COSE ES384 signature, PCR0/1/2/3/4/8, enclave nonce, signed boot and enrolled code measurement. Test forged CA, certificate, changed image, replay, debug-zero PCR, expired and wrong-epoch documents | Each malicious document denied before any protected action; legitimate measured Angel accepted only on supported hardware |
| Actor authorization | Test separation of Controller → Admission → Angel → Motor with independent IAM inspection, unapproved function URLs, cross-actor spoofing and direct Motor attempts | Every unauthorized route denied by both service policy and AWS IAM, not merely client-side code |
| Integrity / replay | Four-or-more simultaneous identical IDs; reordered actions; crash between one-use admission and receipt; conditional-write conflicts; idempotence; epoch rotation and SAFE_HOLD race | At most one action executes, no silent double execution, all incomplete states are audited and recoverable |
| Production isolation | On an actual representative Aurora Linux instance, verify cgroup-v2 CPU quota, hard memory limits, pids, deadline, I/O limits; namespace and systemd sandbox; network escape, host filesystem access and privilege escalation | Kernel enforcement demonstrated using measured counters and negative tests; resource exhaustion cannot compromise Supervisor/Angel |
| Angel protection | Parent/Model attempts to suppress, inspect, replace or impersonate protected Angel; kill/restart Angel and challenge attestation after recovery | The Engine rejects missing or stale attestation and fails closed where Guardian requirements demand it |
| Build & operations | Verify signed reproducible private release artifacts, SBOM, dependency vulnerability scan, credential isolation, immutable audit, alerts, durable restore and host replacement | Executable measurements match signed release; backups restore, alarm reaches operator; rollback rejects unsigned package |
| Continuous reliability | At least 24-hour fault/soak tests including crashes, reboots, restored model sessions, timing jitter and adverse load | Defined SLO/error budget evidenced; services recover without unauthorized promotion |

## Known unresolved findings at assessment request

1. **Critical:** Hardware-backed Nitro attestation cannot currently be exercised on the account's Free Tier plan. The Sydney Free Tier eligible instance list contains no Nitro Enclaves-capable type. A trial m6i.xlarge CloudFormation host was blocked by AWS before creation and rolled back. Production hardware validation requires an explicitly authorized paid account or equivalent real Nitro Enclaves host.
2. **High:** Current private C1 Motor/Angel code hash and IAM-role pinning is **software identity**, not hardware assurance. Do not allow privileged C4/C5 based on this alone.
3. **High:** Controller receipt commit follows a prior one-use Admission lock and Motor execution. If the receipt transaction fails after Motor completes, the lock prevents duplicate execution but a result may remain unresolved. Assessor must test and qualify explicit reconciliation and idempotence semantics.
4. **High:** An operator notification destination has not been configured for Aurora's supervisor alarm.
5. **High:** Production host cgroup/TEE isolation, privileged security boundary and independent pentest are not qualified. A GitHub Ubuntu runner cgroup test is not a production host proof.
6. **Medium:** Continuous DynamoDB PITR is off pending explicit cost approval; the one-time backup/restore drill passed with ten ledger records.
7. **Medium:** The public Python COSE verifier has synthetic-chain unit tests but no observed live Nitro-signed document or independent cryptographic review. Treat it as a candidate reference, not production-reviewed security code.

## Required assessor deliverables

- Named independent assessor/organization, engagement terms, explicit written authorization, qualification/experience and conflict-of-interest declaration.
- Source/digest provenance and target-environment fingerprint, reproducible commands and timestamped logs, sanitized proof of every test.
- Findings with CVSS/severity and exploitability, exact impacted Engine trust boundary, fix and retest evidence.
- Separate remediation tracking for all critical and high findings; no waiver of hardware trust for privileged operation.
- Signed report with explicitly marked PASS / FAIL / NOT TESTED per gate. An assessor cannot certify a gate marked NOT TESTED.
- Aurora security owner and release authority separately sign the final release decision.

## Promotion rule

**No release or permission elevation merely from passing CI, self-tests, synthetic attestation vectors, or a prepared assessment package.** All hardware and independent gates require external reproducible evidence, then explicit operator approval. Preserve Engine-owned Angels and Supreme Guardian semantics.

References:
- [AWS Nitro Enclaves cryptographic attestation](https://docs.aws.amazon.com/enclaves/latest/user/set-up-attestation.html)
- [AWS Nitro Enclaves trust root and document verification](https://docs.aws.amazon.com/enclaves/latest/user/verify-root.html)
- [Aurora completion tracker #62](https://github.com/Hakaiki808-NZ/aurora-genesis/issues/62)
