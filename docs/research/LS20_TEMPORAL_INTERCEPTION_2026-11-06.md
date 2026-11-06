# LS20 observation-based visual planner: temporal-interception experiment
Date: 2026-11-06

## Objective
Complete all seven levels of the public ARC-AGI-3 LS20 game via an agent that reads frames and sends actual game actions. Do not confuse valid moves with a successful game.

## Experiments
| Configuration | Official public LS20 levels | Exploratory score | Actions | Ending |
|---|---|---|---:|---|
| Previous visual search baseline | 5/7 | 53.5714 | 420 | action budget exhausted |
| Energy dominance + multidoor shape learning | 5/7 | 53.5714 | 343 | GAME_OVER |
| Added moving-modifier feedback learning | 5/7 | 53.5714 | 457 | GAME_OVER |
| Added observed motion forecasting and time-expanded intercept | 5/7 | 53.5714 | 431 | GAME_OVER |

## Evidence
- Baseline: https://github.com/Hakaiki808-NZ/aurora-genesis/actions/runs/42176127763
- Dominance/shape learning: https://github.com/Hakaiki808-NZ/aurora-genesis/actions/runs/42176912527
- Modifier feedback: https://github.com/Hakaiki808-NZ/aurora-genesis/actions/runs/42177083946
- Temporal interception: https://github.com/Hakaiki808-NZ/aurora-genesis/actions/runs/42177673040
- Standard regression: https://github.com/Hakaiki808-NZ/aurora-genesis/actions/runs/42177679828

## Result
**No seven-level win achieved.** All test harnesses run and standard tests pass; the game remains incomplete. Temporal interception has not improved level completion. The public LS20 solver is game-specific, informed by observations and publicly documented game mechanics, NOT a blind ARC benchmark agent. Neither private Aurora nor Kyro was exercised.

## Engineering diagnosis
Two key requirements are missing:
1. The environment contains moving modifiers; the complete planner still models many of them as stationary during multistep search. A short-horizon interception heuristic did not repair full planning, showing that a unified action-dependent simulation is needed.
2. Search may find a 40-action plan with low energy and two doors, but recalculation after each real action does not reliably preserve the plan through moving pieces, launchers and spent pickups. The agent fails to manage the three-life limit.

## Next completion gate
- Infer a consistent full observation-driven state machine including movement timing, modifier patrol phases, energy pickups, launch effects, current key, door state, and remaining lives.
- Plan using a time-dependent multi-objective search; validate and correct the model against every live step.
- Add level-six-focused tests measuring *both doors opened before death*.
- Complete level seven with fog-of-war exploration and persistent spatial memory.
- Require official public environment GameState.WIN and levels_completed == win_levels. Retest across runs, then evaluate other public games for transfer.

## Boundary
Do not merge a regressing experimental heuristic into main, or report a test workflow status as game completion.
