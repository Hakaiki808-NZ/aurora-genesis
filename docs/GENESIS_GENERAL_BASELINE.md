# Genesis General v0.1 — general-purpose baseline (experimental)

This adds a runnable local text baseline using Qwen pretrained open weights. It is not AGI, a Kyravantra-trained foundation model, or a public-beta approval.

## Boundaries

Kyro (interface) → Genesis (cognition, memory, reference modules, policy, Guardians) → optional open-weight text generator. Aurora retains execution authority independently. Generated text cannot grant operational privileges.

## Model selection

- Default: Ollama qwen3:1.7b (about 1.4 GB quantized weights, Apache-2.0).
- Alternative: Ollama qwen2.5:1.5b (about 986 MB, Apache-2.0).
- The weights were pretrained by the Qwen team, not Kyravantra. They are not bundled in GitHub or the browser.
- CPU-compatible; no claims yet about inference quality, latency or target-machine benchmarks.
- A separate AWS Qwen2.5-0.5B + LoRA candidate exists; it is not production-qualified or automatically promoted.

## Run on Ubuntu

Install Ollama from its official Linux instructions. Run ollama serve in one terminal if it is not already running as a service. Then execute:

```bash
ollama pull qwen3:1.7b
python3 -m genesis.general_baseline --check
python3 -m genesis.general_baseline --prompt "Explain photosynthesis in three sentences."
python3 -m genesis.general_baseline
```

Use --model qwen2.5:1.5b after separately pulling that model for the smaller alternative. /quit exits and /clear-context clears only recent in-process conversational context, not Genesis persistent data.

## Features and limits

- Local Ollama /api/chat, bounded input and output lengths, last-four-exchange model context, explicit local model allowlist and loopback-only endpoint.
- Existing Genesis rule/policy routing and deterministic arithmetic remain separate from untrusted language-model output.
- No cloud inference, automatic weight download, live web browsing, production remote deployment, or Aurora tool execution.
- Missing weights or unavailable Ollama produce a NOT READY state, not a false claim of neural inference.
- Model can be wrong. Do not rely on it for consequential decisions without independent verification.

## Release qualification

1. Pin and independently verify exact model artifact digest and license.
2. Test real model answers on unseen factual, mathematical, code, multilingual, multi-turn and adversarial prompts. Preserve failures and uncertainty.
3. Review isolation, privacy, retention, JWT identity, rate limits, rollback and Aurora model-admission controls.
4. Verify actual authenticated Kyro chat and deployment/cost safety before enabling hosted serving.
5. Require an explicit human-reviewed go/no-go decision for public beta.

Run python3 -m tests.general_baseline to perform mock-transport tests only. These do not measure model intelligence or prove local weights are installed.

Sources: https://github.com/QwenLM/Qwen3 ; https://ollama.com/library/qwen3:1.7b ; https://ollama.com/library/qwen2.5:1.5b
