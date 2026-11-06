# ARC-AGI-3 typed-action fix and controlled retest
**Date:** 2026-11-06

## Research basis
Official ARC toolkit documentation requires a loop over env.action_space, env.step(GameAction.ACTIONn, data=...), and observation feedback: https://github.com/arcprize/ARC-AGI.
ARC-AGI-3 evaluates long-horizon adaptation as well as task success; outputting a syntactically valid action is not a benchmark achievement.

## Root cause of first failure
The first probe fed an observation and instructions into Genesis v0.1 respond_with_trace() as ordinary chat.
Genesis interpreted the directive as a learnable declaration, answering:
> Learned: You is a exploring an unknown ARC-AGI-3 environment.
The output was not an allowed action, so 0 moves were sent. The official LS20 environment loaded and the exploratory scorecard showed 0.0.

## Fix
- Added genesis/interactive.py: typed, per-game decision and outcome tracking.
- Added Genesis.decide_game_action(game_id, observation, allowed_actions), Genesis.observe_game_outcome(game_id, observation, state), and Genesis.game_history(game_id).
- Rewired the ARC probe to use the typed interface and a strict validator, not chat output.
- Deterministic explore-v1 first probes each allowed action then scores state changes and penalizes repetition. It is a simple exploration baseline, NOT a visual world model or puzzle solver.
- Genesis only recommends actions. The test harness dispatches; this neither replaces nor attests the private Aurora Engine.
- Added regression tests for bounded syntax, feedback, game isolation, pointer coordinates and prevention of accidental fact learning.

## Repeated test: same conditions
- Public ARC-AGI-3 LS20 using official arc-agi SDK, with identical 3-action budget.
- Genesis v0.1 built-in reference backend; Ollama/LLM disabled in BOTH runs.
- Before: 0 valid actions, 0 moves, exploratory score 0.0.
- After: 3 valid actions (ACTION1, ACTION2, ACTION3) executed, exploratory score 0.0, levels completed 0, game state NOT_FINISHED.
- All three observed frame signatures were reported unchanged. No successful solving or goal inference is evidenced.
- New regression tests and entire standard verification suite passed.
- Verified ARC Prize leaderboard result: NONE.

## Evidence
- Original baseline: https://github.com/Hakaiki808-NZ/aurora-genesis/actions/runs/42169270292
- Retest and JSON artifacts: https://github.com/Hakaiki808-NZ/aurora-genesis/actions/runs/42170037620
- Full verification: https://github.com/Hakaiki808-NZ/aurora-genesis/actions/runs/42170037665
- Draft PR: https://github.com/Hakaiki808-NZ/aurora-genesis/pull/5

## Remaining issue
The interface failure is repaired. Puzzle-solving failure is NOT repaired.
Next: faithful frame parsing, visual change detection, state transitions, goal discovery, and planning. Compare heuristic and real visual reasoning backends under identical budgets.
Neither the private Aurora runtime nor Kyro interface was exercised in this public test.