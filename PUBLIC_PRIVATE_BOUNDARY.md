# Public / Private Publication Policy

**Default: private.** Public release requires an explicit content and security review.

## Allowed in the public repository

- Deliberately released Genesis reference source and test fixtures
- Reviewed, minimal Engine/Model interoperability contracts
- Sanitized examples, standards, contributor information and research results
- Public Kyro website assets and selected SDK material

## Excluded from public publication

- Protected Aurora Engine, Angel, admission and recovery implementations
- Security findings, penetration-test evidence, threat and vulnerability inventories
- Live cloud infrastructure inventories, IAM policy detail, internal topology, runbooks and backup locations
- Operational logs, identifiers and identities unnecessary for public client operation
- Credentials, tokens, signing keys, user data, databases, .env files and internal build artifacts
- Unreleased experiments, internal business plans and unapproved drafts

Client-side OAuth configuration and public service URLs may be inherently visible in a deployed browser app; authorization must be enforced by the server, not by obscurity.

Every public merge needs a sensitive-data scan, human review of operational disclosure, and a clear reason for publication. Deleted files may remain accessible in Git history, forks or caches; treat any exposed credential as compromised and rotate it.
