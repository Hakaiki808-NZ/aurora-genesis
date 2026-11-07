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


## Proposed public product naming (RFC only)

Public **model** marketing will use `Genesis 1` for its first independently tested release generation and reserve a pinned ID such as `genesis-1` when an actual qualified, immutable model snapshot exists. Compatible model releases may follow `Genesis 1.1` / `genesis-1-1` as appropriate. This scheme, akin to the distinct model names/IDs used by other model providers, is **not a claim** that the current `v0.1` source baseline or AWS research inference qualifies as Genesis 1.

Public **Kyro** product names are `Kyro Personal`, `Kyro Education`, and `Kyro Business`. They describe interface suites, not separate neural-model weights or engine generations. `Kyro CC` remains staff-only and is never a public suite. UI product and API revisions have their own release manifests/versions and do not silently alter the Aurora/Genesis paired identity.

See [Kyro suites and Genesis naming RFC](rfcs/2026-11-07-kyro-suites-and-genesis-1-naming.md). The current `VERSION` file remains `0.1` pending a separately tested release.
