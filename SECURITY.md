# Security Policy

## Supported source status

The public source-tree milestone is **v0.2.0-preview.1** (development preview only). No version in this repository is certified production-secure. Public beta and privileged Aurora execution remain **HOLD**.

## Private vulnerability reporting

Do **not** publish exploit details, credentials, user records, cloud security findings, or internal access information in public issues, discussions, PRs, CI output or commits.

Use this repository's GitHub **private vulnerability reporting / security advisory** feature when it is enabled. If unavailable, open a public issue requesting a private security contact, without disclosing the vulnerability itself.

## Public/private architecture

Public material may contain Genesis reference code, standards/contracts, documented interfaces, fictional fixtures and sanitized qualification summaries. The following must remain outside GitHub's public repository:

- Protected Aurora Engine runtime, privileged admission, recovery and security-control implementation.
- Production account credentials, API tokens, JWTs, passwords, signing/private keys, session state and per-user data.
- Deployment packages, private IAM policy details, forensic logs, unreleased vulnerability evidence and real incident payloads.
- Local `.env` configurations, cloud credential files, database exports, state files, backups and sensitive build artifacts.

A public browser OAuth client ID, host name or API base URL can be necessary configuration; **it is not authorization**. All protected APIs must enforce their own authorization.

## Preventing accidental publication

The `public-boundary` CI workflow scans tracked files for prohibited paths and common credential formats, suppresses values in logs and fails the build on detection. It does **not** inspect all Git history, GitHub Actions logs/artifacts, private cloud resources, third-party mirrors, or every possible secret format. Green CI is not security certification.

Before accepting a contribution, review its file list, changes, history implications and privacy exposure, especially anything mentioning Aurora operations.

## If a secret was exposed

1. **Immediately revoke/rotate** the credential at its issuer and restrict affected access.
2. Investigate logs and access history without posting secrets to public GitHub.
3. Remove the material from the working tree and coordinate a **history purge** where necessary; deleting a file in a new commit does not remove earlier public commits, clones or caches.
4. Assess leaked deployment details and update public endpoints or permissions where risk warrants.
5. Record only a sanitized remediation outcome in public; maintain private incident evidence.

Security reports can require urgent mitigation even while feature and release work remains frozen.
