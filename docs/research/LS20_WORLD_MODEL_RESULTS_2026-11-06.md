# Genesis LS20 world-model development — 2026-11-06

## Objective and acceptance
Complete the official public ARC-AGI-3 LS20 game with visual observations and real game actions. A successful job is not a game win. Acceptance requires GameState.WIN and levels_completed == win_levels (7). This is a specialist LS20 research project, NOT a general-purpose AGI or a verified official benchmark score.

## Implemented
- Genesis symbolic search integrated with observed moving-modifier phases, key transformations, pickup energy, door state and player location, using an action-indexed search state.
- A regression-covered temporal planner that only applies a modifier at its predicted location on the corresponding action step.
- Dominance pruning of states with identical key/position/doors/phase and lower energy.
- Observed periodic modifier motion instead of an arbitrary 40-action future cutoff, where enough evidence is available.
- Causal evidence check for shape learning: an observed HUD change is not sufficient unless contact with a shape modifier is plausible. Conflicting transitions are counted rather than blindly overwriting rules.
- Existing Aurora/Genesis interface separation retained; this work does not implement a private Aurora Engine or Kyro frontend.

## Direct official LS20 experiments
All attempts used the official public game with frames from the SDK and the game-aware Genesis planner. The full-game test budget was 500 actions.

| Revision | Run | Levels | Actions | Outcome |
|---|---|---:|---:|---|
| Original model | 42176127763 | 5/7 | 420 | Budget reached |
| Temporal intercept | 42177673040 | 5/7 | 431 | GAME_OVER |
| Unified 40-step temporal search | 42189235654 | 5/7 | 323 | GAME_OVER |
| Periodic phase search | 42189727483 | 5/7 | 323 | GAME_OVER |
| Causal modifier learning | 42190164485 | 5/7 | 351 | GAME_OVER |

All models have exploratory score 53.57142857142857 on these runs; none completed level six or seven.
Final causal-run evidence: https://github.com/Hakaiki808-NZ/aurora-genesis/actions/runs/42190164485

## Verified vs unverified
- Existing and new software regression tests: passed.
- Official public LS20 executed: yes.
- Complete LS20 seven-level win: NO.
- Cross-game transfer: NO evidence.
- Official private ARC-AGI-3 leaderboard: not tested.
- Full Aurora + Genesis + Kyro deployed together: not tested.

## Next true blocker
In level six, multiple moving transformation sources and two locks must be handled in one lifetime/energy schedule. The solver continues to produce viable local movements but cannot reliably choose a globally winning sequence when observed dynamics contradict its plans. Needed: an explicit belief-state model with confidence per learned transition, event-driven replanning, lock-order strategy and resets/lives awareness, then fog-of-war map persistence for level seven.

Do not merge the causal or temporal research branch into the primary Genesis release until full-game performance improves beyond the 5/7 baseline and avoids regressions.
