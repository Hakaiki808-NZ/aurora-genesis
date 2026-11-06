# ARC-AGI-3 baseline: 2026-11-06

## Scope
Repository: Hakaiki808-NZ/aurora-genesis, public v0.1 Genesis reference implementation.
Source: official \`arc-agi\` SDK / \`arcengine\`, public game \`ls20\`.
GitHub Actions run: https://github.com/Hakaiki808-NZ/aurora-genesis/actions/runs/42169270292

**Do not report this experiment as an official ARC Prize verified evaluation.**
This measures a single public game/compatibility and does not demonstrate AGI.

## Recorded execution
- Offline 64x64 synthetic observation-format check: completed.
- Genesis self-check: all reported checks passed.
- Action parser unit tests: passed.
- Official ARC client: authenticated anonymously; fetched 25 environments and loaded LS20.
- Allowed LS20 actions: ACTION1, ACTION2, ACTION3, ACTION4.
- Genesis first output: \`Learned: You is a exploring an unknown ARC-AGI-3 environment.\`
- This output is not a valid action. The runner intentionally did not substitute a guessed action.
- Moves executed: **0**.
- Exploratory scorecard score: **0.0**.
- Verified leaderboard score: **not obtained**.

The offline and live probes used Genesis's **built-in reference backend**, with Ollama/LLM disabled, so they say nothing about the quality of a future integrated model provider. An internal health check passing is not evidence of interactive reasoning performance.

## Aurora and Kyro boundaries
The tested public GitHub repository contains no runnable private Aurora Engine or standalone Kyro interface. Neither is certified by this test. The ARC SDK runner is a test harness, not a substitute for either runtime.

## Immediate blocker
Genesis's generic \`respond_with_trace()\` path can interpret the agent instruction as declarative knowledge and respond with a \`Learned:\` message instead of a structured action. A natural-language chat response is not an ARC action API.

## Completion gates
1. **Observation API:** ingest structured game frames as untrusted observations, not learned user assertions.
2. **Action API:** add a native bounded \`decide_action(observation, allowed_actions)\` capability that emits validated ACTION1..ACTION6 with coordinates as required; abstention is explicit.
3. **State:** preserve per-game observations, actions, outcomes, hypotheses and memory over many steps, separated by game.
4. **Engine:** connect Aurora as the exclusive action dispatcher and enforce budget, isolation, policy and receipts.
5. **Interface:** connect Kyro for test visualization and replay inspection; Kyro must not become the cognition authority.
6. **Evidence:** rerun LS20 and a multi-game public suite, record action counts, game completion, runtime, memory behavior, failure cases, run IDs and official scorecards.
7. **Scientific comparison:** distinguish Genesis-only reference, Genesis+model backend, and integrated Aurora/Genesis/Kyro; never compare inconsistent harness configurations as if equivalent.

## Reproduce
\`\`\`bash
python -m pip install -r requirements.txt arc-agi
python -m tests.arc_agi3_probe --offline --out arc-offline.json
python -m tests.arc_agi3_probe --live --game ls20 --max-actions 3 --out arc-live.json
\`\`\`

The official API may offer an anonymous key for the public game set; registered credentials may be necessary for other environments. Avoid publishing private API keys.

See official documentation: https://github.com/arcprize/ARC-AGI and https://docs.arcprize.org/
