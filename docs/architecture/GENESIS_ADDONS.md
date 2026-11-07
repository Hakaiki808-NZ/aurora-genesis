# Genesis Add-ons — Core + optional university curricula (v0.1 experimental)

## Design objective

An add-on can extend which *reference information* Genesis uses on the next response,
without retraining the model or receiving execution privileges. Existing Genesis
knowledge-module retrieval already feeds source-attributed passages into cognition.
This change adds a unified add-on catalogue, a code-owned Core record, and a
machine-readable university-curriculum map.

**This is not an accredited degree, verified expertise, adaptive teaching system,
neural weight update, live cloud installation, or production marketplace.**

## Add-on classes

| Class | Default | Can disable/uninstall | Effect |
| --- | --- | --- | --- |
| Genesis Core | Yes, bundled with runtime | **No** | Existing conversation orchestration, memory interface, semantic-policy boundary, guardian integration, retrieval, traceability and add-on lifecycle |
| Knowledge reference | Optional | Yes | Attributed passages retrieved during relevant chat turns |
| Language reference | Optional | Yes | Unicode-aware retrieval of beginner language notes |
| University curriculum | Optional | Yes | Attributed passages + programme/year/unit/chapter syllabus map |
| Neural adapter / validated skill | Future | Future, gated | Model-compatible LoRA and/or explicitly authorized tools; **not implemented** |

Core is not a user-installable package, a database row or an overrideable system
prompt. A reserved `genesis-core` ID is rejected by both the legacy knowledge
installation path and the new add-on path. Disable/delete are refused. An
operator who controls deployment source code or the host filesystem can still
alter software; this is *application-level immutability*, not tamper-proof
hardware enforcement.

## Architecture boundary

```text
Kyro catalogue / authorised administrator
                  |
             Add-on API
                  |
    +-------------+-----------------------+
    |                                     |
Genesis Core (bundled)          Optional reference packs
always enabled                 install/enable/disable/delete
    |                                     |
    +----> Genesis cognition <--- SQLite retrieved passages
                    |
             Aurora Engine
        remains independent authority
```

Pack content is untrusted *data*. It must never be promoted to system
instructions, credentials, security policy, executable code, Guardian authority
or Aurora operational approval. The add-on APIs reuse the existing
`X-Genesis-Module-Admin` gate and fail closed unless
`GENESIS_MODULE_ADMIN_TOKEN` is set to a strong token (24+ chars). This
static secret is only appropriate on localhost/private infrastructure, not a
public multi-tenant Kyro service.

## Catalogue

`examples/addons/catalog.json` contains all current **reference examples**:
the built-in Core, Physics Foundations, Spanish Basics, te reo Māori Basics,
Physics BSc Starter and Computer Science BSc Starter. Catalogue presence does
not mean a pack has been installed, activated, purchased or deployed.

The BSc starter packs each provide a sample 3-year programme map, units and
short original subject notes. They are *tiny demonstrations*, not complete
university courses. Programme metadata contains:
`title`, `level` (`bachelor`, `master`, or `doctoral`),
`duration_years` (1–8), and 1–40 `units` containing
`code`, `title`, `year`, `chapter_ids`.
The programme is not a qualification awarded to Genesis or a user.

The old schema-1 packs remain valid. For university curriculum packs,
`category` must equal `degree_track` and a validated `programme` is
required. Other categories cannot include `programme`. Legacy versioned
replacement and storage migration behavior are retained.

## Python example

```python
import json
from pathlib import Path
from genesis import Genesis

pack = json.loads(Path("examples/addons/physics-bsc-starter.json").read_text())

with Genesis(enable_ollama=False) as g:
    assert g.list_addons()[0]["id"] == "genesis-core"
    g.install_addon(pack)
    print(g.addon_syllabus("physics-bsc-starter"))
    print(g.respond("Explain electric fields and Gauss law"))
    g.set_addon_enabled("physics-bsc-starter", False)
    # Core cannot be disabled or uninstalled.
```

## API

- `GET /addons` — installed add-ons, Core first
- `GET /addons/catalog` — read-only reference catalogue (installable examples, not deployment guarantees)
- `GET /addons/{addon_id}/syllabus` — structured programme map; explicitly says no degree or proficiency certification
- `POST /addons` — `{"package": {...}, "replace": false}` (administrator)
- `POST /addons/{addon_id}/status` — `{"enabled": true/false}` (administrator)
- `DELETE /addons/{addon_id}` — optional packs only (administrator; Core is HTTP 409)

`/modules` endpoints are maintained for compatibility. Core-ID reservations
apply there as well.

## Tests

```bash
python -m tests.addons
python verify.py
```

Tests check mandatory Core on first boot and restart, the inability to
overwrite/disable/delete it, installation of two degree-track samples,
persistence, syllabus validation, data-only restrictions, activation affecting
next retrieval and older knowledge-module behavior. Testing the local
reference implementation does **not** certify a live AWS deployment.

## Before a public commercial add-on marketplace

- Independent publisher signatures and pinned package hashes, trusted source
  verification, version rollback and licensed content provenance.
- Authenticated Kyro user identities, tenant isolation, scoped purchases and
  rights revocation; Aurora remains responsible for actual execution admission.
- A separate competency evaluation layer with benchmarked subject exams,
  calibrated confidence and coverage metrics. A reference pack alone cannot
  turn Genesis into a degree-qualified practitioner.
- For neural extensions: compatible base-model hashes, PEFT/LoRA adapter
  loading, memory budgets, regression tests, rollback and per-inference
  selection. No weights are downloaded or activated by this change.
- Human review of educational content, including appropriate te reo Māori
  language and cultural review where applicable.
