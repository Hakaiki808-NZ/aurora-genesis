# Implementation Provenance

Aurora v0.1 reference build 8 was created against the canonical Aurora pre-v0.1 build-7 documentation, final Engine report, final audit record and public Generation-1 behavior contract available in the A.I Engineering project.

The stored `AURORA_V1.01_Engine_Reference_Build7_Final.zip` was visible in the project library but its raw archive bytes were not materializable into this execution session. Therefore v0.1 is **not claimed to be a byte-for-byte patch of the Build 7 source tree**. The reference code was reconstructed to preserve the documented pre-v0.1 behavior and interfaces, then extended with the v0.1 hardening mechanisms.

Compatibility was checked through:
- 38 executable core v0.1 regression checks derived from the canonical pre-v0.1 contract and final documentation;
- preservation of all documented v0.1 logical endpoints plus the compatible `EXECUTION.REQUEST` extension;
- direct integration with the real Genesis v0.1 reference implementation;
- 50 dedicated hardening checks and 20,000 randomized MAP mutation cases.

This provenance note is retained so later engineering work can reconcile the v0.1 tree against the original Build 7 source if/when its raw bytes are available in the same execution environment.
