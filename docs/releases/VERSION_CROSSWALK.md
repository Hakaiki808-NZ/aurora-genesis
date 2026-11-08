# Version crosswalk — 8 November 2026

| Scope | Identifier | Current interpretation |
| --- | --- | --- |
| Public GitHub repository | **v0.2.0-preview.1** | Development source snapshot only, recorded in `VERSION`, `README.md`, and `VERSIONING.md`; v0.1 is the earlier pre-alpha baseline. |
| Aurora — Engine | **V1.02** | Canonical Engine architectural release identity; private operational implementation is excluded from this public repository. |
| Genesis — Model | **V1.02** | Canonical Model architectural release identity; public reference and AWS experiments do not prove production deployment of that full version. |
| Exact Engine+Model pairing | **V1.02.102** | Engine major/update + Model major/update in `V<ENGINE_MAJOR>.<ENGINE_UPDATE>.<MODEL_MAJOR><MODEL_UPDATE>` format. |
| Kyro site / cloud infra | Build and migration metadata | Does **not** create a third Engine/Model product release number or change the paired version. |

The public `v0.2.0-preview.1` source line is not an Aurora/Genesis system release and is not tagged as `V1.02.102`. Compatible changes follow the established public development version policy until a documented release milestone. Incompatible architecture changes require formal review; paired-system version advances must be evidence-backed. The public site may display both identifiers *with this distinction*.

**No GitHub Release was present when this audit started.** Publishing static website information does not make the restricted workspace a public product release.
