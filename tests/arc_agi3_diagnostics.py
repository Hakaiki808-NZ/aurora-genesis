"""Public ARC-AGI-3 frame-only diagnostic. Never accesses game source/internals."""
from __future__ import annotations

import json
import numpy as np
import arc_agi
from arcengine import GameAction


def matrix(observation):
    raw = observation.frame
    a = np.asarray(raw)
    # The documented payload can be a sequence of animation frames.
    if a.ndim == 3:
        return a[-1].astype(np.int16)
    if a.ndim == 2:
        return a.astype(np.int16)
    raise ValueError(f"Unexpected observed frame dimensions: {a.shape}")


def summarize(label, observation, previous=None, rows=False):
    a = matrix(observation)
    colors, counts = np.unique(a, return_counts=True)
    change = None if previous is None else int(np.count_nonzero(a != previous))
    print("OBSERVATION " + json.dumps({
        "label": label, "shape": list(a.shape),
        "color_counts": {str(int(x)): int(y) for x, y in zip(colors, counts)},
        "changed_pixels": change,
        "state": getattr(observation.state, "name", str(observation.state)),
        "levels_completed": getattr(observation, "levels_completed", None),
    }))
    if rows:
        palette="0123456789abcdef"
        print("MAP_BEGIN " + label)
        for y,row in enumerate(a.tolist()):
            print(f"{y:02d} "+''.join(palette[v] if 0 <= v <= 15 else '?' for v in row))
        print("MAP_END " + label)
    return a


def main():
    arc = arc_agi.Arcade()
    env = arc.make("ls20")
    if env is None:
        raise RuntimeError("LS20 environment unavailable")
    print("ACTIONS", [a.name for a in env.action_space])
    obs = env.reset()
    prev = summarize("initial", obs, rows=True)
    for i,act in enumerate((GameAction.ACTION1,GameAction.ACTION2,GameAction.ACTION3,GameAction.ACTION4,GameAction.ACTION4,GameAction.ACTION2,GameAction.ACTION4,GameAction.ACTION1)):
        obs = env.step(act)
        if obs is None:
            print("NO_OBSERVATION", i)
            break
        prev = summarize(f"after_step_{i+1}_{act.name}", obs, previous=prev, rows=(i in (3, 7)))
        if obs.state.name != "NOT_FINISHED":
            break


if __name__ == "__main__":
    main()
