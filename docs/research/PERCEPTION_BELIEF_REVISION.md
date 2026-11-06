# Genesis — Perception and Belief Revision v0.1

Status: **research prototype; no real-world sensor attestation or production deployment**.

## Architecture and scope

Kyro (presentation) → Genesis (structured observations + evidence ledger + belief states) → Aurora (unchanged, independent execution authority).

This code does not create or authorize tools, invoke network services, start a camera/microphone, add autonomous agents or modify model weights. All ingested values are **claims**, not facts. The only built-in live source is the host UTC clock, sampled explicitly. The host clock is **not** an Aurora-attested time source.

The existing `Store.facts` memory is deliberately unchanged: in v0.1 the general learning path may overwrite user-asserted facts. The new perception ledger does **not** promote such data into conventional memory, so it does not silently overwrite verified belief state or change tool authorization. Integration with reasoning requires a separate gated semantic-review milestone.

## Schema

- `perception_sources`: immutable source registration with kind and independence group. Mirrors of the same upstream provider belong to one group; source registration itself is **not authentication**.
- `perception_observations`: append-only-per-event records with UTC observed/received/expiry times, typed scalar values, source ID, entity and attribute, unique idempotency key.
- At most 8,192 events are retained, with no arbitrary raw prompt capture; observation values themselves can be sensitive and are kept private to authorized in-process code.
- Source revisions supersede older observations from that source by observation timestamp. Out-of-order arrivals stay in history but cannot roll back a newer reading.
- Observations expire by TTL; old reports are never treated as current merely because they were once corroborated.

## Belief-state semantics

| State | Meaning |
|---|---|
| `unknown` | No observation events have been recorded for the key |
| `supported` | One current reported value, without independent corroboration |
| `corroborated` | Same current value reported by 2+ independent source groups |
| `contested` | Two or more different current values; no single accepted value |
| `stale` | Historical events exist but none is current |

These states are **not calibrated probabilities or guarantees of truth**. When sources disagree, the result includes alternatives and returns `value=None`; it never selects a winner based on a fabricated trust score. This v0.1 model assumes an entity/attribute pair is single-valued at a given time; multivalued attributes need explicit schemas in a later version.

## Programmatic example (trusted host code, not public API)

```python
from genesis import Genesis
with Genesis() as g:
    p = g.perception
    p.register_source("station-a", source_kind="external_feed", independence_group="station-a")
    p.register_source("mirror-a", source_kind="external_feed", independence_group="station-a")
    p.register_source("station-b", source_kind="external_feed", independence_group="station-b")
    p.observe(source_id="station-a", event_id="sample-001", entity="sample-room",
              attribute="temperature_c", value=20.5, ttl_seconds=60)
    p.observe(source_id="station-b", event_id="sample-002", entity="sample-room",
              attribute="temperature_c", value=20.5, ttl_seconds=60)
    assert g.belief("sample-room", "temperature_c")["status"] == "corroborated"
    g.observe_local_clock() # actual OS clock, unverified by Aurora
```

The host application must independently authenticate adapters before calling these methods, enforce privacy/consent and avoid exposing source registration to untrusted users. A string `source_id` is not a digital signature. A real-world feed adapter has not yet been connected; the example demonstrates the ingestion contract.

## Read-only interface

`GET /perception/status` returns **aggregate counts only** (no entities, values, raw evidence or source IDs) for future Kyro diagnostics. `GET /awareness` includes this aggregate snapshot. No public HTTP observation or label-writing endpoints were added.

## Tests and completion gates

Run `python -m tests.perception`, then `python verify.py`. Tests cover missing evidence, independent-source grouping, duplicate mirrors, contradiction, source updates, late arrivals, stale readings, restart persistence, idempotent replay, malformed values/timestamps, storage separation and content-free status.

Outstanding before production:
1. Real authenticated, consented adapters for specific public information or sensors; no arbitrary background surveillance.
2. Genuine authenticated Aurora sensor attestations and protected observation channels; keep the Engine boundary.
3. Formal privacy policy, data access controls, encryption and retention/export/deletion pathways.
4. Belief-to-reasoning integration that safely distinguishes observational claims from accepted user facts and untrusted tool text.
5. Ground-truth evaluation: adversarial reports, sensor fault injection, false-corroboration tests, concept drift, calibration and multi-valued schemas.

## Research context

- Huang et al. (2026), *From Memory to Belief: A Survey of State Maintenance and Belief Revision in LLM Decision Agents*. https://papers.ssrn.com/sol3/Delivery.cfm/7493158.pdf?abstractid=7493158&mirid=1
- Jenkins (2026), *AGM-BENCH: Do Large Language Models Revise Beliefs Rationally?* https://openreview.net/pdf?id=2s1BujG84C
- Elchafei et al. (2026), *Contradictory Evidence in LLMs*. https://aclanthology.org/2026.findings-emnlp.1838/
