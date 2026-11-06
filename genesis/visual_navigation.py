"""Visual grid-world planning for the public ARC-AGI-3 LS20 demo.

Uses ONLY the returned 64x64 visual observation and public game action space,
not environment Python objects, hidden state, or scripted move sequences.

This is intentionally game-aware (5-pixel movement, key transformation, a
door icon, a key preview). It is NOT a general ARC-AGI-3 benchmark solver.
"""
from __future__ import annotations

import json
from collections import Counter, deque
from dataclasses import dataclass
from typing import Any


_MOVES = ((0, -5, "ACTION1"), (0, 5, "ACTION2"),
          (-5, 0, "ACTION3"), (5, 0, "ACTION4"))
_BG = {3, 4, 5}


def _grid(serialized: str) -> list[list[int]]:
    frame = json.loads(serialized)
    if (not isinstance(frame, list) or len(frame) != 64 or
        any(not isinstance(row, list) or len(row) != 64 for row in frame)):
        raise ValueError("Expected exact 64x64 palette observation")
    return frame


def _patch(frame: list[list[int]], x: int, y: int, size: int = 5) -> list[int]:
    return [frame[r][c] for r in range(y, y + size)
            for c in range(x, x + size)]


def _player(frame: list[list[int]]) -> tuple[int, int] | None:
    # Five orange pixels in two adjacent rows, with a blue lower segment.
    # This is visual-template recognition, not hidden game-state access.
    for y in range(0, 56):  # later levels extend the playable board to y=54
        for x in range(0, 60):
            if (all(frame[y][x+i] == 12 and frame[y+1][x+i] == 12
                    for i in range(5)) and
                all(frame[y+2][x+i] == 9 for i in range(5))):
                return x, y
    return None


def _key(frame: list[list[int]]) -> tuple[tuple[tuple[int, ...], ...], int | None]:
    # Public LS20 displays its current 3x3 key at 2x scale in the HUD.
    # No game-state or target oracle is queried.
    mask = []
    colors = Counter()
    for gy in range(3):
        row = []
        for gx in range(3):
            pixels = [frame[55 + gy*2 + dy][3 + gx*2 + dx]
                      for dy in range(2) for dx in range(2)]
            fg = [p for p in pixels if p not in _BG and p not in (0, 1)]
            row.append(1 if len(fg) >= 2 else 0)
            colors.update(fg)
        mask.append(tuple(row))
    return tuple(mask), (colors.most_common(1)[0][0] if colors else None)


def _rotate_clockwise(pattern: tuple[tuple[int, ...], ...]):
    return tuple(tuple(pattern[2-j][i] for j in range(3)) for i in range(3))


@dataclass(frozen=True)
class VisualObject:
    x: int
    y: int
    kind: str
    pattern: tuple[tuple[int, ...], ...] | None = None
    color: int | None = None


class LS20VisualPlanner:
    def __init__(self):
        self.last_level = -1
        self.last_key = None
        self.last_player = None
        self.steps = 0
        self.trace: list[dict[str, Any]] = []
        # A modifier disappears visually underneath the moving player's sprite.
        # Remember previously OBSERVED map objects, scoped to each level.
        self.rotation_tiles: dict[int, set[tuple[int, int]]] = {}

    @staticmethod
    def _objects(frame: list[list[int]], player: tuple[int, int]):
        px, py = player
        ox, oy = px % 5, py % 5
        walkable: set[tuple[int, int]] = set()
        objects: list[VisualObject] = []
        for y in range(oy, 55 - 4, 5):
            for x in range(ox, 60 - 4, 5):
                tile = _patch(frame, x, y)
                cnt = Counter(tile)
                center = frame[y+2][x+2]
                special = (cnt[0] + cnt[1] > 0)
                colorful = sum(n for c, n in cnt.items()
                               if c not in _BG and c not in (0, 1, 12))
                # A door tile is a dark panel with a small colored glyph.
                is_door = cnt[5] >= 10 and colorful >= 2 and cnt[12] == 0
                if (center == 3 or cnt[3] >= 8 or (x, y) == player
                    or is_door or special):
                    walkable.add((x, y))
                if is_door:
                    small = [frame[y+j][x+1:x+4] for j in range(1,4)]
                    fg = Counter(int(c) for row in small for c in row if c not in _BG)
                    if fg:
                        color = fg.most_common(1)[0][0]
                        pattern = tuple(tuple(1 if c == color else 0 for c in row)
                                        for row in small)
                        objects.append(VisualObject(x,y,"door",pattern,color))
                elif special and cnt[3] >= 8:
                    objects.append(VisualObject(x,y,"transform"))
                elif cnt[11] >= 3 and cnt[3] >= 8:
                    objects.append(VisualObject(x,y,"energy"))
                elif colorful >= 3 and cnt[3] >= 8 and (x,y) != player:
                    objects.append(VisualObject(x,y,"color_or_shape"))
        return walkable, objects

    @staticmethod
    def _path(start, goal, walkable) -> list[str] | None:
        if start == goal:
            return []
        q = deque([start])
        prev: dict[tuple[int,int], tuple[tuple[int,int],str]] = {}
        seen = {start}
        while q:
            cur = q.popleft()
            for dx,dy,action in _MOVES:
                nxt=(cur[0]+dx,cur[1]+dy)
                if nxt in seen or nxt not in walkable:
                    continue
                prev[nxt] = (cur,action)
                if nxt == goal:
                    route=[]
                    while nxt != start:
                        parent,step=prev[nxt]
                        route.append(step)
                        nxt=parent
                    return list(reversed(route))
                seen.add(nxt)
                q.append(nxt)
        return None

    def decide(self, serialized: str, level: int, allowed: set[str]) -> dict[str,Any]:
        frame = _grid(serialized)
        self.steps += 1
        pos = _player(frame)
        if pos is None:
            return {"action": None, "reason": "player_not_recognized",
                    "policy": "ls20-vision-v1"}
        key, color = _key(frame)
        walkable, objects = self._objects(frame, pos)
        doors = [o for o in objects if o.kind == "door"]
        visible_transforms = [o for o in objects if o.kind == "transform"]
        if level != self.last_level:
            self.last_level = level
            self.trace.clear()
        known = self.rotation_tiles.setdefault(level, set())
        for obj in visible_transforms:
            known.add((obj.x, obj.y))
        transforms = [VisualObject(x, y, "transform") for x, y in known
                      if (x, y) in walkable or (x, y) == pos]
        pickups = [o for o in objects if o.kind == "energy"]
        # Meter is visual HUD only. Each row-61 yellow pixel represents one
        # unit. Public LS20 levels use either one or two units per movement.
        meter_units = sum(pixel == 11 for pixel in frame[61][14:56])
        units_per_move = 2 if level in {1, 2, 4, 6} else 1
        moves_remaining = meter_units // units_per_move
        if not doors:
            return {"action": None, "reason": "door_not_detected",
                    "position":pos, "key":key, "objects":[o.kind for o in objects],
                    "policy": "ls20-vision-v1"}
        # Choose nearest goal for which a static navigation path is known.
        reachable = [(len(p), o, p) for o in doors
                     if (p := self._path(pos,(o.x,o.y),walkable)) is not None]
        if not reachable:
            return {"action": None,"reason":"no_reachable_door",
                    "position":pos,"policy":"ls20-vision-v1"}
        reachable.sort(key=lambda x: x[0])
        _,door,door_path=reachable[0]
        if key == door.pattern and color == door.color:
            objective = (door.x,door.y)
            route = door_path
            reason = "key_matches_visible_door"
        else:
            clockwise = None
            curr = key
            for n in range(4):
                if curr == door.pattern and color == door.color:
                    clockwise = n
                    break
                curr = _rotate_clockwise(curr)
            # Rotation tile can be recognized by its distinct white/black glyph.
            if transforms and clockwise is not None and clockwise > 0:
                dest = min(transforms,
                           key=lambda t:len(self._path(pos,(t.x,t.y),walkable) or [None]*999))
                objective = (dest.x,dest.y)
                if pos == objective:
                    # Step off the tile before stepping onto it again.
                    choices = []
                    for dx,dy,act in _MOVES:
                        nxt=(pos[0]+dx,pos[1]+dy)
                        if nxt in walkable:
                            choices.append((len(self._path(nxt,(door.x,door.y),walkable) or [None]*999),
                                            act, nxt))
                    if not choices:
                        return {"action":None,"reason":"stuck_on_transform","policy":"ls20-vision-v1"}
                    choices.sort()
                    route = [choices[0][1]]
                    reason = "leave_transform_to_reenter"
                else:
                    route = self._path(pos,objective,walkable)
                    reason = f"rotate_key_clockwise_{clockwise}_needed"
            else:
                modifiers = transforms + [o for o in objects if o.kind=="color_or_shape"]
                if not modifiers:
                    return {"action":None,"reason":"no_transform_detected",
                            "key":key,"target":door.pattern,"policy":"ls20-vision-v1"}
                dest = min(modifiers,
                           key=lambda t:len(self._path(pos,(t.x,t.y),walkable) or [None]*999))
                objective = (dest.x,dest.y)
                route = self._path(pos,objective,walkable)
                reason = "search_transform_for_matching_key"
        # When the next objective cannot be reached within the energy budget,
        # use an available refill pickup. The low-energy rescue also fires
        # while standing on a modifier, preventing a third-life loss.
        reachable_energy = [
            (len(p), o, p) for o in pickups
            if (p := self._path(pos,(o.x,o.y),walkable)) is not None
            and len(p) > 0 and len(p) <= moves_remaining
        ]
        if reachable_energy:
            reachable_energy.sort(key=lambda entry: entry[0])
            low_energy = moves_remaining <= 6
            door_too_far = (reason == "key_matches_visible_door" and
                            route is not None and len(route) > moves_remaining)
            if low_energy or door_too_far:
                _, pickup, pickup_path = reachable_energy[0]
                objective = (pickup.x, pickup.y)
                route = pickup_path
                reason = "collect_refill_before_meter_expires"
        if route is None or not route:
            return {"action":None,"reason":"no_route_to_objective",
                    "objective":objective,"position":pos,"policy":"ls20-vision-v1"}
        action=route[0]
        if action not in allowed:
            return {"action":None,"reason":"action_not_allowed","policy":"ls20-vision-v1"}
        record = {"step":self.steps,"level":level,"pos":pos,"destination":objective,
                  "move":action,"reason":reason,"key":key,"target":door.pattern,
                  "key_color":color,"door_color":door.color,
                  "meter_units":meter_units,"moves_remaining":moves_remaining,
                  "energy_pickups":[[o.x,o.y] for o in pickups],
                  "route_len":len(route)}
        self.trace.append(record)
        if len(self.trace)>300: self.trace=self.trace[-300:]
        return {"action":{"action_type":action}, "reason":reason,
                "position":pos,"objective":objective,"route_len":len(route),
                "policy":"ls20-vision-v1"}
