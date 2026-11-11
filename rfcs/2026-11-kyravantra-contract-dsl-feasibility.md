# RFC (Research Only): Kyravantra Contract Language / KDL feasibility

**Date:** 2026-11-08
**Status:** Research; no adoption decision, compiler, runtime interpreter, or production policy authority
**Track:** Independent research workstream, separate from Genesis reliability and Kyro public-beta gates
**Decision:** Preserve Python, JavaScript/TypeScript and existing AWS/HTTP tooling. Evaluate an optional, small contract authoring layer, **not** a general-purpose programming language.

## 1. Problem and non-goals

Aurora (Engine), Genesis (Model) and Kyro (Interface) need consistent descriptions of tool capabilities, principal/tenant scope, data visibility, request/receipt shapes, versioning and approval requirements. Inconsistent hand-written declarations are a risk. The strongest immediate approach may be *existing* schemas and policies, not another programming language.

Non-goals:
- No replacement for Python, TypeScript, Rust, model runtimes, Terraform or CloudFormation.
- No model-generated permissions, executable AI macros, just-in-time privilege grants or automatic deployment.
- No KDL evaluator in the trusted Aurora execution path.
- No direct disclosure of private Aurora signing/containment internals in this public RFC.
- No new work that delays the active model-quality, login or release gates.

## 2. Existing solutions to benchmark first

| Candidate | Strong fit | Limitation / evaluation question |
| --- | --- | --- |
| JSON Schema Draft 2020-12 | Stable shape validation and interop for API payloads | Cannot by itself make authorization decisions |
| Cedar | Typed principal/action/resource authorization, policy-schema validation; explicit deny-oriented controls | Need to verify integration cost, policy lifecycle, auditability and Engine enforcement alignment |
| OPA / Rego | General policy-as-code for structured requests and infrastructure | Operational complexity and broad policy language may be unnecessary for bounded permission maps |
| CUE | Typed constraints, validation, configuration and generated data | Not an authorization enforcement engine; benchmark language/toolchain cost |
| KDL syntax + compiler (hypothesis only) | More readable, Kyravantra-specific contracts and provenance | Requires parser, formal semantics, validator, compatibility guarantees, signed output and long-term maintenance |

Official starting references:
- JSON Schema: https://json-schema.org/specification
- Cedar: https://docs.cedarpolicy.com/ and https://docs.cedarpolicy.com/validation.html
- OPA: https://www.openpolicyagent.org/docs/policy-language
- CUE: https://cuelang.org/docs/

## 3. Preferred baseline before writing any DSL parser

Use:
1. JSON Schema for machine-readable request/response/module formats and strict validation.
2. A reviewed authorization policy engine (trial Cedar and Rego) for decisions appropriate to each enforcement boundary.
3. Generated TypeScript/Python types from one versioned schema where practical.
4. Aurora independently checks every action, issuer, authorization proof, expiry, replay status and Engine policy before execution. A generated contract can constrain but never **grant** Engine capability by itself.

First test whether a lightweight YAML/JSON authoring convention plus validation solves the problem. Avoid a custom parser when standard tools suffice.

## 4. KDL hypothesis, deliberately non-executable

Illustrative future syntax only, **not** valid/current system code:

```text
contract "workspace.write" version "0.1" {
  requester: Genesis
  enforcer: Aurora
  principal_scope: "tenant"
  approval: "explicit-human"
  audit: "required"
  default: "deny"
}
```

Possible compilation target: a canonical JSON contract checked against a versioned JSON Schema; optionally generate *reviewed* Cedar or Rego policy inputs. The syntax must never directly produce authorization without an independent enforcement policy.

## 5. Required semantics and security properties

- Fixed grammar; no expressions, scripting, filesystem access, network access, imports or dynamic evaluation.
- All capabilities, principals, resource types and actions must be allowlisted and type checked.
- Unknown fields, duplicate definitions, missing schema version, conflicting permissions, unsafe scope widening or unsupported versions: **compile error**, not permissive fallback.
- Deterministic canonical output and reproducible hash; sign and verify approved release artifacts before policy intake.
- Human review of semantic diffs and change control; strict tenant isolation; expiry and revocation apply to proof-bearing requests.
- Test conflicting policies, malformed inputs, adversarial prompt-generated text, schema migration and compatibility.
- Meaningful audit trails that link source contract, generated artifact, review, enforcement decision and receipt.
- A public contract must not contain signing keys, private Engine internals, identity records or user data.

## 6. Research experiments (offline; zero deployment changes)

**Experiment A — Baseline:** Express 10 representative cross-system contract cases in JSON Schema plus Cedar, and JSON Schema plus Rego. Measure correctness, auditability, effort and ambiguity.

**Experiment B — CUE:** Encode the same 10 schemas/constraints in CUE. Compare generated JSON and validation errors.

**Experiment C — KDL sketch:** Write a grammar and a **non-executing** parser/validator prototype only if A/B expose a concrete problem. Compile to reviewed, versioned JSON; compare 10 positive and at least 30 negative/adversarial examples against baseline semantics.

**Experiment D — Interop:** Confirm outputs are accepted by Python and TypeScript clients and do not change Aurora authorization outcomes.

Collect: test failures, input size/complexity, engineering time, review time, runtime/CI cost, version-migration hazards and security observations. Reuse external standards; do not invent cryptographic or authentication primitives.

## 7. Adoption gate

KDL is **rejected or parked in Later/Research** unless experiments demonstrate a clear, repeatable advantage over JSON Schema plus Cedar/Rego/CUE without weakening authority isolation.

If selected, require:
- Independent security and usability review;
- A published grammar, conformance corpus, deterministic validator and migration/version strategy;
- CI checks with invalid/adversarial cases and source-to-output reproducibility;
- A design that emits contracts only, with Engine-side independent authorization remaining authoritative;
- Explicit approval in a separate architecture RFC and no automatic production rollout.

## 8. Track ownership and completion gate

**Primary engineering objective stays:** improve Genesis correctness, demonstrate actual model quality and browser-authenticated Kyro chat, and close production safeguards.

**Research output is complete when:** comparison table, reproducible examples, failure-mode assessment and GO/NO-GO recommendation are documented. KDL implementation is optional and explicitly not a release prerequisite.

**Disposition:** Independent research track. No runtime, secrets, cloud deployment or policy authority modified by this RFC.
