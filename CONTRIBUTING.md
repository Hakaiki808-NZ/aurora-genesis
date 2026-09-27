# Contributing

Thank you for helping improve AURORA / Genesis.

## Contribution principles

1. Preserve the separation between cognition and execution authority.
2. Do not move Engine-owned operational authority into Genesis.
3. Do not introduce hidden network access, credentials or machine-specific state.
4. Add tests for behavioral changes.
5. Keep experimental claims clearly identified as experimental.
6. Architecture changes require an RFC.

## Workflow

1. Open or select an issue.
2. Discuss material design changes before implementation.
3. Create a focused branch.
4. Add or update tests.
5. Submit a pull request describing:
   - problem,
   - proposed change,
   - architectural impact,
   - security impact,
   - test evidence,
   - alternatives considered.

## RFCs

Use `rfcs/0000-template.md` for architecture-affecting proposals.

## Scope discipline

Bug fixes, tests, documentation, evaluation and compatible implementation improvements are preferred over reopening settled architecture without evidence of a concrete flaw.

## Developer Certificate of Origin

Contributions use a DCO-style sign-off. Contributors should certify that they have the right to submit their contribution by adding a `Signed-off-by:` line to commits, for example:

`Signed-off-by: Your Name <your-email@example.com>`

Use `git commit -s` to add the sign-off automatically.
