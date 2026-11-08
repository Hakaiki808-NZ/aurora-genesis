# Aurora · Genesis · Kyro

**Status:** Experimental development source. Not a production release.

This repository contains public research references, examples, compatibility contracts and the Kyro website source.

- **Aurora:** independent execution Engine (protected implementation is private).
- **Genesis:** cognition/Model research and published reference code.
- **Kyro:** user-facing Interface and website.

## Public resources

- [Systems overview](docs/architecture/SYSTEMS_PUBLIC_GUIDE.md)
- [Genesis public interfaces](MODEL_API.md)
- [Genesis standards](docs/standards/GENESIS_COMMON_AI_BASELINE_V1.md)
- [Examples](examples/)
- [Kyro public website](cloud/public-site-v1/)
- [Project maturity](docs/governance/PROJECT_STATUS.md)
- [Security and disclosure](SECURITY.md)
- [Public/private policy](PUBLIC_PRIVATE_BOUNDARY.md)

## Security and boundaries

Public source does **not** grant access to protected runtime operations or imply that internal Engine implementations are open source. No production credentials, deployment inventories, incident evidence, operational security findings or private user data belong here.

**Do not submit secrets or vulnerabilities in public issues or pull requests.**

Development and qualification are ongoing. Production readiness, broadly available accounts and high-consequence Engine execution are not established by the presence of reference code.

## Development

Run `python3 verify.py` for the public reference test suite. Contribution and security rules are in [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

Code explicitly distributed in this repository is under [Apache 2.0](LICENSE). This does not license undistributed proprietary Engine code.
