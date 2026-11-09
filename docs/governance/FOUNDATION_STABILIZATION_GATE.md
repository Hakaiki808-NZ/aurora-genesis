# Foundation stabilization gate

**Status:** Active development freeze from 2026-11-09. This is a source contribution gate, **not** a claim of production qualification.

## Release objective

Deliver a verified Aurora execution/recovery boundary, a reliable bounded Genesis inference path, and repeatable authenticated Kyro → Genesis → Aurora end-to-end qualification. Keep the established Engine / Model / Interface authority separation unchanged.

## Kyro scope freeze

Do not merge new user-facing product features, new suites, new voice features, marketplace capabilities, or visual redesigns while the foundation gate is active. Existing open Kyro feature branches may remain as drafts. No new Kyro feature deployment is authorized by this document.

**Permitted:** narrowly scoped fixes for existing interfaces, identity/authorization flaws, session continuity, accessibility defects, integration failures, regression tests, and security maintenance.

A pull request modifying `web/kyro/`, `cloud/public-site-v1/`, `cloud/public-beta-web/`, or `cloud/kyro-launch/` must have a maintenance-class title and an explicit `Kyro-freeze-exception: stabilization` line in its description. CI checks this basic rule for pull requests; reviewers must still validate that it is actually maintenance. Direct pushes and external/private deployment paths are not technically controlled by this public CI guard.

## Completion gates (evidence required)

1. **Aurora:** verify independent admission, opaque supervised health, denial/fail-closed paths, bounded worker recovery, isolation and protected logs. A passing reference unit suite is not hardware-attested production authorization.
2. **Genesis:** verify CPU inference produces correct non-empty answers within specified latency and memory limits; test unavailable backend and retries; persist and restore state; prevent generated text from taking Engine authority. Keep third-party model output explicitly identified.
3. **Cross-system:** exercise anonymous denial; valid identity → Kyro → Genesis chat; resource timeout / fallback; memory/session continuity; denied unauthorized Engine action; authorized consent and receipt; retry/idempotency and tenant isolation.
4. **Operations:** verify alarms have effective notifications or remediation and demonstrate at least one restoration drill. Record actual metrics and test dates in private qualification evidence, not in public source.

## Release decision

The next Kyro feature phase can open only when the responsible maintainers have recorded affirmative evidence for each gate; unresolved security or reliability failures keep the gate closed. Do not treat documentation, mocked tests, successful CI, or healthy AWS control-plane configurations as equivalent to authenticated live qualification. No automatic promotion to public beta.

Public PRs must never disclose protected Engine source, internal incidents, secrets, user data, credentials, security configuration, or detailed production infrastructure.
