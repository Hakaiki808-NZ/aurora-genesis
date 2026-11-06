# Genesis v0.1 Model API

Use `genesis.Genesis` as the stable Model entry point. Do not read or mutate the SQLite database directly from an interface layer.

## Construction

```python
from genesis import Genesis
model = Genesis(state_path="state.db", workspace="workspace", enable_ollama=False)
```

## Public methods

- `respond(message) -> str`
- `respond_with_trace(message) -> {answer, trace}`
- `state() -> dict`
- `self_check() -> dict`
- `constitution() -> dict`
- `policy_audit(limit=50) -> list`
- `search_knowledge(query, limit=8) -> list`
- `goal(goal_id) -> dict | None`
- `decision_history(limit=20) -> list`
- `register_tool(name, description, fn, mutating=False, **policy)`
- `pending_engine_actions(limit=100) -> list`
- `reconcile_engine_receipt(receipt) -> dict`
- `export_state(path) -> Path`
- `backup_state(path) -> Path`
- `close()`

## Installable knowledge modules (v0.1 reference)

- `install_knowledge_module(package, replace=False)`
- `list_knowledge_modules()`
- `search_knowledge_modules(query, limit=5)`
- `enable_knowledge_module(module_id, enabled=True)`
- `uninstall_knowledge_module(module_id)`

HTTP: `GET /modules`, `GET /modules/search?q=...`, authenticated `POST /modules`, `POST /modules/{module_id}/status`, and `DELETE /modules/{module_id}`. Mutations require a strong `GENESIS_MODULE_ADMIN_TOKEN` and matching `X-Genesis-Module-Admin` header. Data-only packs are not executable, signed publisher products or purchased credentials. See `docs/architecture/KNOWLEDGE_MODULES.md`.

Free reference and language packs use distribution=open. List and search results expose is_free and, for language packs, category and language_tag. Starter examples: examples/modules/spanish-basics.json and examples/modules/te-reo-maori-basics.json. This currently provides knowledge retrieval, not automatic multilingual fluency or speech.

## Registered-tool metadata

Tools can declare:
- `mutating`
- `policy_flags`
- `external_side_effect`
- `irreversible`
- `sensitive_data`
- `policy_declared`

Unknown mutating capabilities without policy metadata are conservative by default.

An `external_side_effect=True` tool is not directly dispatched by Genesis. The selected action is persisted as PREPARED and converted into an Aurora Engine request.

## Engine receipt integration

`reconcile_engine_receipt()` accepts a `genesis.engine_boundary.EngineReceipt` for a known PREPARED request. It applies terminal states `COMMITTED`, `FAILED` or `CANCELLED`, enforces receipt-ID anti-replay and makes exact duplicate reconciliation idempotent.

## HTTP adapter

`python serve.py` binds to `127.0.0.1:8766` by default.

Routes:
- `GET /health`
- `GET /state`
- `GET /diagnostics`
- `GET /constitution`
- `GET /policy-audit?limit=...`
- `GET /goals`
- `GET /goals/{goal_id}`
- `GET /tools`
- `GET /knowledge?q=...&limit=...`
- `POST /chat` with `{ "message": "...", "trace": true|false }`

The HTTP adapter is a Model interface only. It is not the Aurora Engine Contract.


## Seven capability opt-in foundation (pre-alpha)

The optional programmatic UserCapabilityServices profile store adds
deny-by-default personal memory and preference records, claim/source dossiers
that cannot self-declare verification, pull-only due suggestions and
deterministic user-supplied weighted decision comparison.

Construct with Genesis(..., profile_id="local"), then use ux_consents(),
ux_set_consent(scope, enabled), ux_remember(kind,key,value),
ux_recall(kind), ux_forget(kind,key), ux_add_claim(statement,sources),
ux_review_claim(claim_id,supported,reviewer),
ux_propose_nudge(title,due_at), ux_attention(), ux_dismiss_nudge(id),
ux_compare_options(criteria,options), ux_export_profile() and
ux_erase_profile().

**Privacy limitation:** these new consent controls apply only to new ux_*
SQLite tables. They do NOT govern older respond() episode/fact/goal
storage, logs, backups or provider data. Do not describe the whole system
as consent-gated; the legacy store requires separate migration.

**Security limitation:** no HTTP routes are exposed for these features;
Kyro must authenticate users, authorize a profile, and bind reviewer identity.
The profile_id constructor is an application trust boundary and cannot be
treated as authentication. No Aurora tools are invoked by these services.
See [Seven Capability Integration](docs/architecture/SEVEN_CAPABILITY_INTEGRATION.md).

## Guardian hardening notes (v0.1)

`state()` now reports the Challenge Omega and Guardian jury size. Consequential external actions are prepared only after Intent Capsule, Constitution, Kernel, capability and Guardian checks produce a complete Model authorization and a valid Model Authorization Proof. The public API still exposes no Supreme or Engine-handler control surface.
