# Aurora, Genesis and Kyro — Public Systems Guide

**Published:** 7 November 2026 (NZDT)  
**Public development line:** v0.1 pre-alpha  
**Architectural pairing:** Aurora V1.02 + Genesis V1.02 = V1.02.102 (design identity, not cloud certification)  
**Access model:** research and public information; authenticated Kyro workspace remains invite-only.

## At a glance

We are building an AI research platform that separates **execution**, **cognition**, and **interaction**. The public website is the information and discovery presence; **Kyro itself is the interface used to work with Genesis and approved services**.

| Layer | Responsibility | Explicitly not |
| --- | --- | --- |
| **Aurora — the Engine** | Runtime, lifecycle, resource admission and allocation, independent execution authorization, operational integrity and protected observability | A reasoning model that decides what requests mean |
| **Genesis — the Model** | Cognition, planning, semantic authorization, reasoning and memory-related research, modular knowledge experiments | An authority that can grant itself access to Engine execution |
| **Kyro — the Interface** | Web/mobile-facing user interaction, account-bound projects, collaboration, code/research views and permitted service calls | An Engine or a replacement for Genesis |
| **Public website** | Information, docs, research journal, roadmap, read-only previews | Account-backed Kyro, an open production signup or an execution gateway |

### The defining boundary

> Genesis governs cognition; Aurora governs execution. Kyro connects people with the systems without gaining either system's protected authority.

The Engine Contract is an explicit compatibility boundary; the Model requests a capability but cannot give itself operational permission. Aurora's Supreme Guardian has Engine-only operational authority. Genesis's Alpha and Omega Guardians handle Model semantic governance. Aurora-owned Angels provide independently controlled inspection/interlock signals; they are not Model-appointed Guardians. This guide intentionally describes the concepts rather than disclosing protected implementation details.

## What the public software can show today

**Genesis** has an open-source reference model and tests, an experimental modular knowledge prototype, short free Spanish/te reo Māori reference packs, a physics foundations reference pack, and neural/weight-training experiments. Adding a reference pack is **not** equivalent to training model weights, demonstrating fluent translation, earning a university degree, or acquiring accredited specialist expertise.

**Kyro** has a static read-only web preview and an invite-only AWS-backed workspace research beta. Reference work includes projects, role-controlled invitations, shared files, project messages, private conversation storage, and developer UI candidates. It does not yet establish unrestricted autonomous code execution, simultaneous co-editing, a paid marketplace, or broadly available user signup.

**Aurora** has public contracts, boundary verification material and a restricted cloud development foundation. Its security-critical runtime internals stay private. A reference test passing does not certify containment, physical hardware trust, or production safety.

## AWS alignment (verified resource inventory, 7 November 2026)

- **Region:** AWS Sydney (`ap-southeast-2`).
- **Edge:** enabled CloudFront distribution serving versioned, static S3 website prefixes `/site/`, `/discover/` and `/v3/`.
- **Public information site:** `https://d3j65cc3p66kzr.cloudfront.net/site/index.html`.
- **Kyro workspace:** `https://d3j65cc3p66kzr.cloudfront.net/v3/index.html` (invite-only/authentication-gated).
- **Backend:** AWS API Gateway and Lambda development services are provisioned; production-equivalent user journeys and safeguards still need validation.
- **Caution:** successful AWS resource inspection is not a successful independent human-browser acceptance test.

## How the systems work together

1. A person uses **Kyro** to request help or work with a project.
2. **Genesis** interprets the task and may propose a reasoned or tool-assisted action within approved Model capabilities.
3. If external side effects are needed, **Aurora** independently evaluates the operational request under its own policies and resource controls.
4. **Kyro** displays outcomes and appropriate status without being granted hidden Engine or Model security powers.

This architecture supports future MCP-based tool interfaces and A2A-style agent interoperability where separately approved. References to a standard do not imply every adapter is deployed today.

## Versioning and transparency

The public GitHub development version is currently **v0.1**. Separate architecture decisions identify **Aurora V1.02** and **Genesis V1.02**, paired as **V1.02.102**. A Kyro/web build, AWS schema migration or CI run can have separate build metadata; it must not silently change the paired product identity. See [version crosswalk](../releases/VERSION_CROSSWALK.md).

Source and public releases: [aurora-genesis on GitHub](https://github.com/Hakaiki808-NZ/aurora-genesis). The public repository uses Apache-2.0 for its included code; this does not license excluded proprietary Aurora components.

## Scope of publication

**Share:** public Genesis reference code, intentionally public specs/contracts, research results with honest limitations, documentation, examples, safe deployment templates, contributor processes and non-sensitive tests.

**Do not share:** Aurora restricted runtime code, private credentials, signing material, protected containment and recovery internals, customer data, private infrastructure parameters, or security-sensitive operational configuration.

## What remains before a general public beta

Real browser login and multi-user acceptance, privacy and data lifecycle decisions, mobile/accessibility validation, actionable alerting, restore/rollback drills, verified IAM and API isolation, independent cost controls, abuse review, and model/Engine assurance. Public informational pages can be published while general-public onboarding remains on **HOLD**.

Related material: [release qualification gate](../releases/PUBLIC_BETA_GATE_2026_11_07.md), [knowledge modules](KNOWLEDGE_MODULES.md), [public/private boundary](../../PUBLIC_PRIVATE_BOUNDARY.md), and [contribution guide](../../CONTRIBUTING.md).
