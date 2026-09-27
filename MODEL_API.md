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


## Guardian hardening notes (v0.1)

`state()` now reports the Challenge Omega and Guardian jury size. Consequential external actions are prepared only after Intent Capsule, Constitution, Kernel, capability and Guardian checks produce a complete Model authorization and a valid Model Authorization Proof. The public API still exposes no Supreme or Engine-handler control surface.
