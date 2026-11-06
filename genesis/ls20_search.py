"""Resource-constrained visual game search for the public ARC-AGI-3 LS20 demo.

This public-game-specific research adapter uses pixels from the 64x64 frame,
plus openly documented game mechanics (rotation, color cycle, energy). It must
not be presented as a blind ARC-AGI-3 evaluation or as general intelligence.
No game source, hidden engine attributes, or predetermined paths are consulted.
"""
from __future__ import annotations

import json
from collections import Counter, deque
from dataclasses import dataclass
from typing import Any

from .visual_navigation import (
    LS20VisualPlanner, VisualObject, _grid, _key, _patch,
    _player, _rotate_clockwise, _MOVES,
)

COLOR_CYCLE = (12, 9, 14, 8)  # palette indices learned from the visual color tile
MAX_NODES = 175_000


@dataclass(frozen=True)
class SearchWorld:
    walkable: frozenset[tuple[int,int]]
    door: tuple[VisualObject, ...]
    rotation: frozenset[tuple[int,int]]
    color: frozenset[tuple[int,int]]
    energy: tuple[tuple[int,int], ...]
    player: tuple[int,int]
    key_shape: tuple[tuple[int,...],...]
    key_color: int
    meter_units: int
    unit_cost: int


class LS20SearchPlanner:
    """Searches position, key orientation/color, pickups, and energy budget.

    This is a prototype symbolic world model over observations, separate from
    the deterministic navigator. It caches only observed object locations and
    never reads hidden game variables.
    """
    def __init__(self):
        self.visual = LS20VisualPlanner()
        self.cache: dict[int, dict[str,set[tuple[int,int]]]] = {}
        self.last_level = -1
        self.searches = 0
        self.fallbacks = 0
        self.last_stats: dict[str,Any] = {}

    def perceive(self, serialized: str, level: int) -> SearchWorld | None:
        f = _grid(serialized)
        pos = _player(f)
        if pos is None:
            return None
        key_shape, key_color = _key(f)
        if key_color is None:
            return None
        walkable, objects = self.visual._objects(f, pos)
        rotation: set[tuple[int,int]] = set()
        color: set[tuple[int,int]] = set()
        energy = []
        doors = []
        for o in objects:
            point = (o.x,o.y)
            if o.kind == "door":
                doors.append(o)
            elif o.kind == "transform":
                rotation.add(point)
            elif o.kind == "energy":
                energy.append(point)
            elif o.kind == "color_or_shape":
                cell = _patch(f, o.x, o.y)
                present = {v for v in cell if v in COLOR_CYCLE}
                if len(present) >= 3:
                    color.add(point)
        seen = self.cache.setdefault(level,{"rotation":set(),"color":set()})
        seen["rotation"].update(rotation)
        seen["color"].update(color)
        rotation |= seen["rotation"]
        color |= seen["color"]
        # A sprite hides the underlying modifier when standing on it.
        walkable |= rotation | color | {pos}
        meter_units = sum(p == 11 for p in f[61][14:56])
        unit_cost = 2 if level in (1,2,4,6) else 1
        return SearchWorld(
            walkable=frozenset(walkable),
            door=tuple(doors),
            rotation=frozenset(rotation),
            color=frozenset(color),
            energy=tuple(sorted(energy)),
            player=pos,
            key_shape=key_shape,
            key_color=key_color,
            meter_units=meter_units,
            unit_cost=unit_cost,
        )

    @staticmethod
    def search(world: SearchWorld) -> tuple[list[str] | None, dict[str,Any]]:
        """Breadth-first search with exact move cost and consumable refills."""
        if world.key_color not in COLOR_CYCLE:
            return None, {"reason":"unknown_color"}
        if not world.door:
            return None, {"reason":"no_visible_goal"}
        if not world.walkable:
            return None, {"reason":"no_navigation_map"}
        if len(world.energy)>8:
            return None, {"reason":"too_many_pickups_to_model"}

        patterns=[world.key_shape]
        for _ in range(3):
            patterns.append(_rotate_clockwise(patterns[-1]))
        start=(world.player, 0, COLOR_CYCLE.index(world.key_color), 0, world.meter_units)
        queue=deque([start])
        visited={start}
        parents:dict[tuple,tuple[tuple,str]]={}
        energy_bit={point:1<<i for i,point in enumerate(world.energy)}
        goal_locations={(o.x,o.y):o for o in world.door}
        expanded=0
        while queue and expanded < MAX_NODES:
            state=queue.popleft()
            expanded+=1
            (x,y),rot,ci,mask,meter=state
            for dx,dy,action in _MOVES:
                nxt=(x+dx,y+dy)
                if nxt not in world.walkable:
                    continue
                after_meter=meter-world.unit_cost
                pickup_mask=energy_bit.get(nxt,0)
                newmask=mask
                if pickup_mask and not (mask & pickup_mask):
                    newmask|=pickup_mask
                    after_meter=42
                if after_meter < 0:
                    continue
                newrot = (rot+1)%4 if nxt in world.rotation else rot
                newcolor = (ci+1)%len(COLOR_CYCLE) if nxt in world.color else ci
                lock=goal_locations.get(nxt)
                if lock:
                    if (patterns[newrot] != lock.pattern or
                        COLOR_CYCLE[newcolor] != lock.color):
                        continue
                end=(nxt,newrot,newcolor,newmask,after_meter)
                if end in visited:
                    continue
                visited.add(end)
                parents[end]=(state,action)
                if lock:
                    route=[]
                    cur=end
                    while cur!=start:
                        parent,mv=parents[cur]
                        route.append(mv)
                        cur=parent
                    route.reverse()
                    return route, {"reason":"solved_symbolic_search",
                                   "expanded":expanded,"visited":len(visited),
                                   "length":len(route),"refills_modelled":len(world.energy)}
                queue.append(end)
        return None, {"reason":"no_goal_path_found",
                      "expanded":expanded,"visited":len(visited),
                      "reached_cap":expanded>=MAX_NODES,
                      "refills_modelled":len(world.energy)}

    def decide(self, serialized: str, level: int, allowed: set[str]) -> dict[str,Any]:
        self.searches+=1
        world=self.perceive(serialized,level)
        if world is None:
            return {"action":None,"policy":"ls20-search-v1",
                    "reason":"visual_perception_failed"}
        route,stats=self.search(world)
        self.last_stats=stats
        if route:
            action=route[0]
            if action not in allowed:
                return {"action":None,"policy":"ls20-search-v1",
                        "reason":"invalid_search_action"}
            return {
                "action":{"action_type":action},
                "reason":"resource_constrained_search",
                "policy":"ls20-search-v1",
                "route_len":len(route),
                "position":world.player,
                "objective":route[-1],
                "meter_units":world.meter_units,
                "search_stats":stats,
            }
        # Fallback is explicitly tagged; it cannot be claimed as a solved plan.
        self.fallbacks+=1
        out=self.visual.decide(serialized,level,allowed)
        out["policy"]="ls20-search-v1-fallback"
        out["search_stats"]=stats
        return out
