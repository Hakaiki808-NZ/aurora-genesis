# Genesis Agent Team V1 — bounded reference implementation

**Status:** Implemented as an opt-in, on-demand, text-only role orchestrator. No production or independent security qualification is claimed.

## Purpose and system boundaries

`genesis/agents.py` uses an explicitly configured `GeneratorBackend` to generate separate drafts from four role prompts (Research, Developer, Tester, Auditor), then synthesizes them with a fifth Coordinator call. The backend may be the configured local Ollama or opt-in Bedrock adapter; no new provider credentials or tools are installed. **A different role prompt is not a separately trained model.** Outputs are drafts, not verified execution evidence.

- **Genesis**: specialist reasoning, coordination and uncertainty reporting.
- **Aurora**: execution, containment, attestation, protected authority, and any future action authorization. The reference agent team does not call Aurora.
- **Kyro**: future UI with explicit operator identity, consent, activity feed and review controls; not implemented here.

## Runtime contract

- Explicit `/agents/run` request only; no scheduler, self-spawning, background execution or persistence.
- Maximum four specialists plus one synthesizer per request; no loop or recursion; 4,000-character task cap, 4,000-character output per call.
- Model backend must be available; otherwise a `blocked` status is returned, without invented results.
- No shell, files, network tools, write permissions, GitHub/AWS mutation, or privileged Engine requests are delegated to agents. Backend network requests, if any, are governed by the already configured model provider and infrastructure.
- API endpoint uses existing `GENESIS_CONTROL_TOKEN` protection and is disabled if the token is unset or weak. Kyro must authenticate users before forwarding requests.
- All results have `verified: false`, `human_review_required: true`, `tools_executed: 0`, `engine_actions: 0`. A complete inference pass returns `draft_unverified`, never `completed` or `verified`.
- Generated text and the user task are untrusted; prompt delimiters are advisory, not a formal prompt-injection security boundary. Never promote generated text into tool authority.

## API

`GET /agents/roles` — authenticated role list.

`POST /agents/run` — authenticated request body:

```json
{"goal":"Assess module reliability","roles":["research","tester","auditor"]}
```

The header is `X-Genesis-Control-Token`. Responses include roles, per-role draft/blocked statuses, coordinator synthesis, call count and verification flags. `roles` can be omitted to run all four specialists.

## Local smoke test

```bash
python -m unittest tests.test_agents
python verify.py
```

For a real inference check, configure Genesis's existing neural backend and strong server-side token, then make one authenticated request. Tests using a stub backend confirm orchestration logic only; they do not demonstrate live model availability, factual accuracy, safe tool execution or cloud deployment.

## Next gated increments

1. Add evidence-backed tasks linked to the existing TaskLedger, keeping human attestation separate.
2. Add read-only, policy-declared tool proposals with independent Aurora enforcement (not an LLM-only allowlist).
3. Add Kyro operator controls, event auditing and cost budgets; investigate cancellation and timeout enforcement at the deployment layer.
4. Run adversarial and provider-backed acceptance tests before considering mutating actions.
