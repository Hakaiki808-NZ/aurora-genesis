# GitHub full-repository consolidation — 7 November 2026

**Repository:** https://github.com/Hakaiki808-NZ/aurora-genesis  
**Scope:** Public GitHub source and CI only; no authenticated AWS deployment, model invocation, account changes or private Aurora source release.  
**Source:** Main at commit \`7b2060043bd76057f601b1607a2f94007f871c40\` (at audit), PR/issue listings and GitHub Actions; report under consolidation PR.  
**Release posture:** v0.1 **pre-alpha**; hold general-public beta. No published GitHub release at audit.

## Completed in this update

| Item | Disposition | Link |
|---|---|---|
| PR #41: protected Genesis Core and data-only university add-on catalogue | **Merged** after current-head test success; no academic credential or weight update claim | https://github.com/Hakaiki808-NZ/aurora-genesis/pull/41 |
| PR #37: disabled-by-default Genesis neural gateway source and AWS template | **Merged** after current-head test success; **do not enable** while quota and cost blockers remain | https://github.com/Hakaiki808-NZ/aurora-genesis/pull/37 |
| PR #43: GCAB-1 common AI baseline and evidence gap register | **Merged** after current-head test success | https://github.com/Hakaiki808-NZ/aurora-genesis/pull/43 |
| Issue #8: LS20 Level 6/7 | **Closed as duplicate**, explicitly **not resolved**; outstanding requirements tracked in #10 | https://github.com/Hakaiki808-NZ/aurora-genesis/issues/8 |
| Issue #44: Genesis blind general-model evaluation | **Opened as P0 blocker**, with reproducible acceptance criteria | https://github.com/Hakaiki808-NZ/aurora-genesis/issues/44 |

## Final consolidation addendum (after the initial 20-PR snapshot)

The initial open-PR inventory below is intentionally a time-stamped snapshot, **not** the latest count.

- **PR #45 merged:** authoritative README, project status and whole-repo audit refreshed; latest-head CI passed.
- **PR #46 merged:** corrected a dormant/fallback `IntentCapsule.from_action` signature and added an authorization regression; latest-head CI passed.
- **PR #2 closed as superseded, not merged:** its minimal, tested repair was extracted into #46 instead of merging conflicting old changes.
- **Current open PR count after closing #2: 19**; the 19 remaining proposals are #42, #40, #36, #35, #33, #31, #23, #22, #20, #18, #15, #13, #12, #11, #9, #7, #5, #4 and #3.
- **Current open issues:** #1, #6, #10, #30, #38 and #44 (six). #8 remains closed as a duplicate of #10.
- **Final consolidation main commit at this addendum:** `c88fb2de394c988c985f032c369cb2865e865db2`. The documentation addendum itself will create a newer commit when merged.
- Main CI immediately before this addendum: older main integration runs green; a newer complete-suite run was still executing when sampled. CI must be checked again after the addendum merge.

**No release was published.** Public beta remains HOLD; no inference activation, training spend, Engine privilege expansion or branch deletion occurred.

## Current source-of-truth documents

- [GCAB-1](../standards/GENESIS_COMMON_AI_BASELINE_V1.md): capability baseline, gap register and test protocol.
- [Public beta gate](PUBLIC_BETA_GATE_2026_11_07.md): existing HOLD decision and operator safeguards.
- [System architecture](../architecture/SYSTEMS_PUBLIC_GUIDE.md): Aurora Engine, Genesis Model, Kyro Interface boundary.
- [Project status](../governance/PROJECT_STATUS.md): high-level current status.
- [Neural gateway](../../cloud/genesis-neural-gate/README.md): **disabled**, quota-blocked, no real-model production chat claims.

## Outstanding P0 blockers — do not close without evidence

1. **#44 — Model:** licensed model selection, verified *real* neural inference, blind GCAB-1 reasoning/code/multilingual/context/safety evaluations, cost/latency reporting. The tiny AWS character-model training proof is not an operational general LLM.
2. **#30 — Browser:** approved invite-only PKCE account flow, end-to-end Kyro chat/persistence/isolation, actual browser/mobile checks, recovery drills.
3. **Public beta release gate:** privacy notice/data deletion, security/abuse and access review, actionable alarms, tested rollback/restore, enforceable cost/kill-switch procedure, go/no-go record.
4. **Aurora:** the AWS Engine instance is restricted C1 reference service. Do not extrapolate local reference hardening test passes to approved cloud privilege execution.

## Open pull-request triage at audit

**20 open PRs remain** after the three merges. They are not all finished or merge-safe merely because isolated CI passes. Their heads/branches are preserved; no whole-branch merges or deletions have been undertaken in this consolidation.

| PR | Workstream | Next disposition |
|---|---|---|
| #42 | hierarchical memory/associative network | Review privacy/tenant isolation, performance and behavior; opt-in draft |
| #40 | local general neural text baseline | Validate licensed weights, real generation/latency and GCAB-1 tests before merge |
| #36 | Genesis naming / Education and Business suites RFC | Product/governance review, no production change |
| #35 | temporary authenticated Kyro chat interface | Browser PKCE and authenticated real-use acceptance required |
| #33 | Hugging Face import/PEFT investigation | Review model licensing, checkpoint provenance, scope of 88 commits, tests and cost |
| #31 | interactive public website stacked on V5 frontend | Rebase/reconcile with already-published main public-site assets |
| #23 | alternate Hugging Face backend | Resolve duplication with #33; do not merge competing backends blindly |
| #22 | AWS perception adapter stacked on #18 | Review upstream dependency and boundary tests |
| #20 | mobile/PWA/Expo stacked on V5 frontend | Hold for security, app-store and functional testing |
| #18 | perception/belief revision stacked on #15 | Review source trust and behavioral evaluation |
| #15 | experimental functional-awareness interfaces | Research-only; do not infer consciousness |
| #13 | Kyro frontend completion stacked on V5 | Reconcile/de-duplicate frontend assets and tests |
| #12 | V5 workspace source snapshot | Reconcile with main V3 assets, live AWS and rollback test |
| #11 | LS20 temporal world model stacked on #9 | Experimental; no verified terminal win |
| #9 | LS20 search optimisation stacked on #5 | Experimental; no verified terminal win |
| #7 | early authenticated Kyro cloud beta stacked on #3 | Review historic version and current canonical cloud path |
| #5 | ARC-AGI-3 LS20 experiment | Experimental; official-game score is not a general AGI benchmark |
| #4 | earlier AWS foundation | Reconcile with deployed/current infrastructure before selectively importing |
| #3 | localhost Kyro alpha | Reconcile overlapping capabilities with V3 and preserve tests selectively |
| #2 | intent-context regression | **Historical at initial audit only:** subsequently extracted into merged #46, then #2 closed as superseded |

**Issue disposition:** #1 external review open; #6 game action API open; #10 LS20 win open; #30 browser acceptance open; #38 marketing and feedback open; #44 blind model qualification open. #8 closed as duplicate.

## Test and release policy

- All three merged PR heads had successful current-source GitHub Actions tests; follow-up main CI runs must be checked after this consolidation lands.
- Green CI is **not** equivalent to real-model benchmark success, browser acceptance, private-Aurora secure deployment, or public-beta qualification.
- No public GitHub Release was published in this audit. Preserve \`v0.1\` as pre-alpha. Creating a release tag or widening access requires a separately reviewed artifact/change-log and go/no-go.
- Source updates do **not** activate Bedrock, train models, deploy web pages, spend on GPU, or create customer accounts.
- Branch pruning is deferred: several stacked PRs point at other unmerged branches. Delete only after checking dependency and preserving any needed changes.

## Completion gates for next GitHub cycle

- [x] Merge qualified, focused, current-head CI-green work.
- [x] Document the industry-derived baseline and actual limitations.
- [x] Merge source for strictly disabled neural gateway.
- [x] Close one demonstrable duplicate while retaining its owner issue.
- [x] Create clear P0 issue for real model quality.
- [x] Extract obsolete #2 fallback intent-context fix into current main with explicit CI and close #2 as superseded.
- [ ] Selectively reconcile remaining draft stacks and competing Hugging Face backends after reviewing actual diffs.
- [ ] Run real GCAB-1 general-model evaluation and publish reproducible results.
- [ ] Close #30 only after real browser and data-isolation evidence.
- [ ] Complete beta security/operations gates and record formal go/no-go.
- [ ] Approve a future prerelease/tag only on audited source with completed CI.

**Decision:** consolidate **public source safely** now; keep live cloud, privileged execution, training and external onboarding unchanged.
