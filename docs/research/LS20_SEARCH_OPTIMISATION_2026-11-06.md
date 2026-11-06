# LS20 progress and limits — 2026-11-06

## Objective
Raise the public Genesis prototype from simple ARC-AGI-3 action validation to winning LS20 using observed public 64x64 frames, without hidden game state or scripted solutions.

## Baseline before these changes
Public ARC LS20 run: https://github.com/Hakaiki808-NZ/aurora-genesis/actions/runs/42176127763
- Levels completed: 5 / 7
- Exploratory score: 53.57142857142857
- 420 actions, stopped by action budget
- Goal discovery and movement worked on the earlier levels, but dual-lock level 6 caused repeated oscillation and large searches.

## Implemented improvements
1. **Energy dominance pruning** in the symbolic search. Identical spatial/key/pickup/door states with lower remaining energy are skipped, removing many redundant search expansions.
2. **Shape discovery for multiple locks**: a previously observed shape match for one door no longer ends exploration of unknown transformations that might be necessary for another door.
3. **Mobile modifier outcome learning**: detect visual changes in the displayed key after an action even if the modifier subsequently moved. Pure quarter-turn rotations and likely resets are filtered so they are not mistaken for a shape-cycle edge.
4. Controlled action budget increased to 500 for this experimental branch only.

## Actual public-game retests
- Before mobile-modifier feedback fix: https://github.com/Hakaiki808-NZ/aurora-genesis/actions/runs/42176912527
  - 5 / 7 levels, 53.5714 exploratory score, GAME_OVER at action 343.
- With mobile-modifier feedback fix: https://github.com/Hakaiki808-NZ/aurora-genesis/actions/runs/42177083946
  - 5 / 7 levels, 53.5714 exploratory score, GAME_OVER at action 457.
  - Symbolic search found paths and made first-lock progress within level 6, but failed to complete both locks before lives expired.
  - Run contains exact action traces and visual-state snapshots in the GitHub Actions artifact.

## What passes and what does not
- Standard GitHub verification: PASSED.
- ARC SDK public LS20 environment execution: PASSED.
- Visual perception and navigation: Demonstrated to be effective for five levels.
- Complete seven-level LS20 win: **NOT ACHIEVED**.
- Blind cross-game generalization: **NOT TESTED**.
- Full Aurora/Genesis/Kyro integration: **NOT TESTED**, only the public game-aware Genesis planner.

## Outstanding engineering gap
The search treats modifier cells as static for the duration of a planned route, while later-level modifiers move with player actions. It also searches under a limited observable energy budget, and can follow repeatedly invalidated long plans. Needed next: a short-horizon time-expanded model of moving modifiers, per-transition uncertainty and validation, explicit life-aware planning/checkpointing, and a robust fog-of-war map for level seven.

The game-aware LS20 adapter must not be reported as ARC-AGI-3 general intelligence or official private benchmark performance.
