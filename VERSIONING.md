# Versioning

The first public development release is **v0.1**.

Public version history begins here. Earlier internal development labels are intentionally excluded from the public repository and are not treated as public releases.

Until the project reaches a stable release policy:

- compatible development changes increment the development version;
- breaking architectural changes require explicit review;
- build identifiers and CI run numbers are metadata, not product versions.

No public changelog is included in the initial repository preparation package.

## System-pairing design identity

The public GitHub source line remains `v0.1` (pre-alpha). The separately established Engine/Model architectural pairing is **Aurora V1.02 + Genesis V1.02 = V1.02.102**. Those identities describe different things: the public repository baseline versus the two-system pairing. The pairing is **not** a claim that the public repository or current AWS deployment contains a production-qualified V1.02 Engine.

See [version crosswalk](docs/releases/VERSION_CROSSWALK.md). A future release-tag or version bump requires its own tested release decision.
