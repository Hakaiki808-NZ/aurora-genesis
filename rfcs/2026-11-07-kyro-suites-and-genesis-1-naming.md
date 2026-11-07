# RFC: Kyro product suite family and Genesis model naming

**Status:** Proposed design — documentation only
**Date:** 2026-11-07
**Architecture invariant:** Aurora (Engine), Genesis (Model), Kyro (Interface). No engine authority delegated to Genesis or browser UI.

## Naming conventions

- **Genesis 1**: proposed first consumer-facing model generation name. The API ID `genesis-1` must not be advertised as an immutable production model until a corresponding tested snapshot and provenance/model card are available.
- Compatible replacement generation: `Genesis 1.1`, API ID `genesis-1-1` (example only). Each non-alias model ID must refer to pinned weights and model settings; alias mobility must be explicit.
- **Kyro**: consistent consumer interface/product shell, presenting distinct **Kyro Personal**, **Kyro Education** and **Kyro Business** suites. Developer/API experience may later become **Kyro Developer**.
- **Kyro CC**: exclusively internal, private development/operations/staff command centre. It must not be a public suite, selectable workspace or client-bundled control surface.
- **Aurora**: separately versioned runtime/security authority, retaining all engine-model separation and policy boundaries.

This is a customer-facing naming standard, not an elevation of the public repo version. `VERSION=0.1` is currently the real **pre-alpha public reference source** identifier. The established Aurora V1.02 / Genesis V1.02 structural pairing and paired V1.02.102 identity retain their existing architectural meaning. Release management must carry a separate manifest of pinned engine/model/UI/API versions.

## Public suite experience

Public sign-in should take the user to **Kyro Home**, not Kyro CC. Home lists workspaces the authenticated principal belongs to and only the permitted suites. Switching a suite changes organisation context and user-specific entitlements; it cannot confer permissions. Backend policy must deny by default.

```
Kyro Home (personal user)
  ├── Kyro Personal
  ├── Kyro Education (institution/grade/role)
  │     ├── Early learning / ECE       [supervised]
  │     ├── Primary / Years 0–6       [teacher, student, admin, caregiver]
  │     ├── Intermediate / Years 7–8  [teacher, student, admin, caregiver]
  │     ├── Secondary / Years 9–13    [teacher, student, admin, caregiver]
  │     └── Tertiary                  [lecturer, learner, administrator]
  └── Kyro Business (organisation/role)
        ├── Projects, team collaboration, documents
        ├── Task boards, approvals, audit activity
        └── Scoped specialist knowledge packs
Internal-only Kyro CC — wholly separate control/identity plane.
```

**Critical distinction:** education type configures learning-year, curriculum, school policies and available functionality; *role* configures the view and permissions within that setting. A Year-4 learner must never receive teacher tools merely by selecting a role in the browser. Class rosters, institutional consent and all assessment data are server-authoritative.

## Education proposal — adapt proven LMS primitives

- Teacher: class/subject view, lesson plans, rubric assignment workflows, human-reviewed grading/feedback, class completion insights and approved content selection.
- Student: school-year-appropriate activities, guided learning, accessible hints, work submissions, clear provenance and no access to other learners.
- School administrator: provisioning, curriculum/subject pack policy, privacy and safeguarding configuration, audit, staff access.
- Caregiver: verified-link, consent-and-policy-scoped dependent information only.
- Early learning: educator-mediated interactions and no unsupervised AI chat.
- Learning content packs: licensed/versioned reference assets tagged to year, curriculum, outcomes, language, publisher, rights and approval. Installing material is not training Genesis or granting an accredited degree.

Interoperability priorities: **1EdTech OneRoster 1.2** for school roster/course/grades exchange; **LTI 1.3 Advantage** for secure tool launch/grades and content selection; **CASE 1.1** for curriculum outcome tags. Research: Moodle assignments/rubrics/gradebook, Teams Education Classwork/Assignments, and Canvas course-module sequencing. These are workflow references, not copied vendor code or commitments to certified interoperability.

## Business proposal — reuse bounded V3 collaboration

- Pilot: project owner/editor/viewer, invitations, tasks, messages, shared versioned files, review/approval queue and knowledge library, with actual backend enforcement and revocation.
- Later: collaborative editing with conflict resolution, notifications and workspace presence; M365/Google/GitHub adapters; SAML/SCIM, retention and compliance controls.
- AI context follows least privilege and cannot retrieve other tenants' documents, reveal secrets, or execute side-effect tools without an authorised Aurora decision.

## Deployment/safety gates

1. Do not put private Command Centre implementation or endpoints into public source or public browser bundles.
2. Reconcile existing Cognito user pools only with a user-migration and token-validation design; tenant policy must be checked at every API and storage access.
3. Separate UI demonstration from production capabilities. No student identity data or personal details should be entered into a prototype or unapproved AI tool.
4. Require school vendor due diligence and privacy impact assessment, consent, safeguarding, data deletion/retention, human grading review and verified school/guardian authorisation before live learner onboarding.
5. Align content to current NZ curriculum only after official version review and educator sign-off. The curriculum has 2026 transition changes.
6. Performance, multiuser concurrency, AWS costs, accessibility and release rollback need formal tests before promotion.
7. The existing public beta gate remains **HOLD** until its acceptance checks are closed.

**Current implementation status:** This RFC is a proposal. No live school or enterprise suite, neural model snapshot, real-time multiuser business editing or release certification is claimed here.

## Source guidance

- Anthropic pinned model IDs: https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions
- OneRoster: https://www.1edtech.org/standards/oneroster
- LTI: https://www.1edtech.org/standards/lti
- CASE: https://www.1edtech.org/standards/case
- Moodle assignment workflows: https://docs.moodle.org/501/en/mod/assignment/index
- NZ Ministry of Education generative AI: https://www.education.govt.nz/education-professionals/schools-year-0-13/digital-technology/generative-ai
- NZ Privacy Commissioner digital technologies in education: https://www.privacy.org.nz/resources-and-learning/a-z-topics/protecting-children-and-young-peoples-privacy/childrens-privacy-guidance-for-the-education-sector/chapter-16-digital-technologies/
