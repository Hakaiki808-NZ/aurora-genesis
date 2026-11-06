# Aurora / Genesis / Kyro launch gates

Last reviewed: 2026-11-06. This document is an engineering checklist,
not a certification or a claim that this system is artificial general intelligence.

## Evidence-based milestone table

| Milestone | Gate | Evidence/status |
| --- | --- | --- |
| 1. Reproducible local integrated build | Kyro->Genesis works with authenticated loopback calls; persistence/restart tested; real separate Aurora Engine provides signed receipts | **Partially met:** Kyro->Genesis integration is under CI test; the private Aurora implementation and an end-to-end Engine connection are not contained in this public repo |
| 2. General cognition | Held-out cross-domain generality, learning, causal/world-model and long-horizon tests pass independent thresholds | **Not met:** only bounded symbolic/retrieval/planning functionality currently demonstrated |
| 3. Security and reliability | Threat model, Engine-attached adversarial penetration test, protected Angel isolation, recovery, secret handling, independent review | **Not met:** reference tests and Kyro token gate are not production qualification |
| 4. Private alpha | Usable local chat interface, permission controls, authentication, documented operations, safe backup/restart and invitation-only deployment review | **Partially met:** local single-user research alpha available; no multi-user identity, backups automation, cloud deployment or independent privacy review |
| 5. Launch qualification | Defined benchmark thresholds, replicated evaluations, cost/scale tests, privacy and security review, signed go/no-go | **Not met** |

## Local research-alpha usage

Install prerequisites with `python -m pip install -r requirements.txt`.
Launch with `python launch_local_alpha.py` from the repository root.
Open `http://127.0.0.1:8767`, paste the terminal's access token, and
chat locally. The token is held only in the browser tab's JavaScript memory.

By default this launches a text/rule-based Genesis backend with a C3 capability
ceiling. To opt in to an installed Ollama backend, set
`GENESIS_GENERATOR=ollama` and configure `GENESIS_OLLAMA_MODEL`.
Never run the alpha server with a public host binding or reverse proxy.
No remote login, rate limiting, TLS termination, multi-user isolation, auditing
service, cloud resource controls or Aurora Engine attachment is provided.

Tests:
- `python verify.py`: existing reference suite plus local Kyro HTTP test.
- `python -m evals.baseline --output /tmp/genesis-baseline.json`:
  basic measured cognition regression probes; these are not AGI benchmarks.

## Gate criteria before any real external tool autonomy

1. Aurora must be independently deployed and must verify authorizations
   without relying solely on a Genesis-controlled secret or in-process function.
2. Confirm irreversible and external effects require real human approval
   and auditable, short-lived, single-use authorization.
3. Test compromised model, prompt injection, replay, concurrency and restart.
4. Run isolated environments and verify shutdown, pause and revocation.
5. Collect independently reproducible red-team and failure data.

## Gate criteria before public deployment

- Replace the local token with verified per-user identities and session management.
- Add authentication/authorization, abuse controls, TLS, privacy and data retention policies.
- Establish observability, restore drills, incidents/on-call and disaster recovery.
- Perform a privacy impact assessment in the intended jurisdictions.
- Verify resource/cost limits, load behaviour and a rollback plan.
- Obtain independent review and record a release/no-release decision.

## AGI claim policy

A passing local smoke test does not establish AGI. No human-level AGI
capability claim is authorised by these tests. Broad, novel, held-out and
independently verified benchmarks are required before such a claim is even
considered.
