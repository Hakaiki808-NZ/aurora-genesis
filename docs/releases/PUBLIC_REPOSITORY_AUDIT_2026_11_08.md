# Public repository exposure audit — 8 November 2026

**Target:** `Hakaiki808-NZ/aurora-genesis` (public GitHub repo, default branch `main`)  
**Decision:** security-hardening source preview only; **do not** publish general beta or privately protected Engine internals.  
**Evidence:** default-branch GitHub file tree, selected file contents, branch/PR/release metadata, current main workflow runs, and reference docs. No authenticated private Engine implementation or AWS account audit was performed here.

## What was actually inspected

- Repository inventory: **260 files and directories** in the reported Git tree; no published GitHub Releases at inspection.
- Read direct contents of primary README, SECURITY, public/private boundary, version files, selected qualification/security/cloud docs, AWS templates/configs, front-end config and scripts, neural/training code, workflow definitions and issue templates.
- Ran format-specific token/key-pattern checks over dozens of public code files and reviewed several sensitive-facing documentation files. The GitHub code-search endpoint did not return indexed matches, so a blank code search was **not** considered exculpatory evidence.
- Observed successful main-branch CodeQL and test workflow runs when inspected. Those runs predate the changes in this branch; the new guard must get its own passing CI evidence.

**Limit:** this is a targeted current-tree review, not an exhaustive source-line audit, historical secret scan, dependency vulnerability assessment, GitHub Actions artifact/log review, or private cloud verification. It cannot prove that no credential was ever disclosed.

## Findings and treatment

| Topic | Current finding | Treatment |
| --- | --- | --- |
| Obvious hardcoded credentials | No confirmed active key, private PEM, or long bearer token in files covered by the targeted checks | Add fail-closed tracked-file scanner; separately review *full history*, prior Actions artifacts and external mirrors |
| Browser OAuth identifiers | Public JS and beta config include Cognito authorization URLs, client IDs and API hostnames | These are normally public for PKCE browser clients, **not secrets**. Verify server-side JWT authorization, CORS and PKCE; avoid treating obscurity as protection |
| Operational architecture | Public qualification/status docs name AWS services, restricted Engine flow, operating region and IAM boundary summaries | Intended public evidence but operationally informative. Owner/security reviewer must assess whether to minimize details and move sensitive runbooks to private storage |
| Protected Engine implementation | The inspected default-branch files contain public reference helpers and descriptions; protected Aurora runtime source was not identified | Keep confidential implementation and signing material in private storage. This is **not** proof about older commits or unmerged branches |
| Local/secret artifacts | Original ignore rules covered basic `.env` and DB/log files but not many private key/state and engine-path patterns | Expand ignore rules and block risky tracked paths in CI |
| Source version and docs | `VERSION` was 0.1 and README described a pre-alpha while later work was merged | Move public tree to `0.2.0-preview.1` and clearly distinguish snapshot, model identity, operational qualification and beta approval |
| Public early-interest issues | The issue form explicitly warns that issues are public and forbids email/contact/sensitive details | Retain warnings; do not collect private user data through public GitHub issues |

## Required follow-up — not completed by a source commit

1. **Historical secret review:** scan all refs and reachable Git history with a mature tool such as Gitleaks or TruffleHog under trusted operator control, plus review release artifacts, old CI logs and any forks. If a secret was ever published, rotate/revoke it *before* coordinating history rewrite and GitHub cached-object cleanup.
2. **Repository security controls:** enable private vulnerability reporting, secret scanning/push protection where available, branch protection/rulesets requiring reviewed CI, and dependency updates. Review all GitHub App and Actions permissions.
3. **Operational disclosure review:** decide which AWS resource details, live internal topology and qualification evidence should remain public. Prefer a separate private evidence repository/storage for detailed architecture, runbooks, IAM policies and incident records.
4. **Open PRs and branches:** audit each unmerged branch for sensitive content before merging or publishing a release. Do not delete stacked work blindly.
5. **Real test qualification:** complete the outstanding Aurora hardware/isolation/assurance issue, Genesis model quality gate and Kyro rendered-browser acceptance. Do not equate a green source CI run with end-to-end safety.

## Release gate

`0.2.0-preview.1` is a **source milestone** only. No published GitHub Release or change to cloud access is part of this PR. The public-beta and production Engine decisions remain **HOLD**. Any official prerelease requires a current CI pass, approved release notes, provenance and reviewer sign-off.
