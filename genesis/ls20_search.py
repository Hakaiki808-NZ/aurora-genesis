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
    shape: frozenset[tuple[int,int]]
    energy: tuple[tuple[int,int], ...]
    player: tuple[int,int]
    key_shape: tuple[tuple[int,...],...]
    key_color: int
    meter_units: int
    unit_cost: int
    launches: dict[tuple[int,int],tuple[int,int]]


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
        self.last_action: tuple[int,tuple[int,int],str,tuple[tuple[int,...],...],int] | None = None
        self.observed_transitions: dict[int,dict[tuple[tuple[int,int],str],tuple[int,int]]] = {}
        self.learned_shapes: dict[int,dict[tuple[tuple[int,...],...],tuple[tuple[int,...],...]]] = {}
        self.recent_positions:dict[int,deque[tuple[int,int]]] = {}

    @staticmethod
    def _visible_launchers(frame:list[list[int]], ox:int, oy:int):
        """Infer launch direction from the five-pixel bar along a wall edge.

        A launch is triggered on the adjacent FLOOR cell, and pushes the
        player away from the wall. Only images are read; no internal game data.
        """
        bars={}
        # Scans a little beyond the maze where bars may touch the outer edge.
        for y in range(oy, 56, 5):
            for x in range(ox, 60, 5):
                patch=_patch(frame,x,y)
                n4=patch.count(4)
                n1=patch.count(1)
                if n4<15 or n1<5:
                    continue
                left=all(frame[y+row][x]==1 for row in range(5))
                right=all(frame[y+row][x+4]==1 for row in range(5))
                top=all(frame[y][x+col]==1 for col in range(5))
                bottom=all(frame[y+4][x+col]==1 for col in range(5))
                if left: bars[(x-5,y)]=(-5,0)
                if right: bars[(x+5,y)]=(5,0)
                if top: bars[(x,y-5)]=(0,-5)
                if bottom: bars[(x,y+5)]=(0,5)
        return bars

    @staticmethod
    def _apply_launch(
        target: tuple[int,int], walkable:frozenset[tuple[int,int]],
        doors:set[tuple[int,int]], launchers:dict[tuple[int,int],tuple[int,int]]
    ) -> tuple[int,int]:
        delta=launchers.get(target)
        if delta is None: return target
        current=target
        for _ in range(12):
            nxt=(current[0]+delta[0],current[1]+delta[1])
            if nxt not in walkable or nxt in doors:
                break
            current=nxt
        return current

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
        shape: set[tuple[int,int]] = set()
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
            elif o.kind == "shape":
                shape.add(point)
            elif o.kind == "color_or_shape":
                cell = _patch(f, o.x, o.y)
                present = {v for v in cell if v in COLOR_CYCLE}
                if len(present) >= 3:
                    color.add(point)
        seen = self.cache.setdefault(level,{"rotation":set(),"color":set(),"shape":set()})
        if level < 4:
            seen["rotation"].update(rotation)
            seen["color"].update(color)
            seen["shape"].update(shape)
            rotation |= seen["rotation"]
            color |= seen["color"]
            shape |= seen["shape"]
        else:
            # Moving modifiers start at level five. Treat the CURRENT
            # observation as authoritative; remembered old locations are not
            # active tiles. Retain only an occluded known tile under the player.
            for name,visible in (("rotation",rotation),("color",color),("shape",shape)):
                remembered = seen[name]
                if pos in remembered:
                    visible.add(pos)
                remembered.clear()
                remembered.update(visible)
        # A sprite hides the underlying modifier when standing on it.
        walkable |= rotation | color | shape | {pos}
        meter_units = sum(p == 11 for p in f[61][14:56])
        unit_cost = 2 if level in (1,2,4,6) else 1
        launches=self._visible_launchers(f,pos[0]%5,pos[1]%5)
        return SearchWorld(
            walkable=frozenset(walkable),
            door=tuple(doors),
            rotation=frozenset(rotation),
            color=frozenset(color),
            shape=frozenset(shape),
            energy=tuple(sorted(energy)),
            player=pos,
            key_shape=key_shape,
            key_color=key_color,
            meter_units=meter_units,
            unit_cost=unit_cost,
            launches={key:delta for key,delta in launches.items()
                      if key in walkable},
        )

    @staticmethod
    def search(
        world: SearchWorld,
        overrides: dict[tuple[tuple[int,int],str],tuple[int,int]] | None = None,
        shape_edges: dict[tuple[tuple[int,...],...],tuple[tuple[int,...],...]] | None = None,
    ) -> tuple[list[str] | None, dict[str,Any]]:
        """Breadth-first search with exact move cost and consumable refills."""
        if world.key_color not in COLOR_CYCLE:
            return None, {"reason":"unknown_color"}
        if not world.door:
            return None, {"reason":"no_visible_goal"}
        if not world.walkable:
            return None, {"reason":"no_navigation_map"}
        if len(world.energy)>8:
            return None, {"reason":"too_many_pickups_to_model"}

        redirects = overrides or {}
        shape_edges = shape_edges or {}
        start=(world.player, world.key_shape, COLOR_CYCLE.index(world.key_color), 0, world.meter_units)
        queue=deque([start])
        visited={start}
        parents:dict[tuple,tuple[tuple,str]]={}
        energy_bit={point:1<<i for i,point in enumerate(world.energy)}
        goal_locations={(o.x,o.y):o for o in world.door}
        goal_points=set(goal_locations)
        expanded=0
        while queue and expanded < MAX_NODES:
            state=queue.popleft()
            expanded+=1
            (x,y),pattern,ci,mask,meter=state
            for dx,dy,action in _MOVES:
                nominal=(x+dx,y+dy)
                nxt=redirects.get(((x,y),action),nominal)
                if nxt==nominal and nominal in world.walkable:
                    nxt=LS20SearchPlanner._apply_launch(
                        nominal,world.walkable,goal_points,world.launches)
                if nxt == (x,y) or nxt not in world.walkable:
                    continue
                after_meter=meter-world.unit_cost
                pickup_mask=energy_bit.get(nxt,0)
                newmask=mask
                if pickup_mask and not (mask & pickup_mask):
                    newmask|=pickup_mask
                    after_meter=42
                if after_meter < 0:
                    continue
                newpattern = _rotate_clockwise(pattern) if nxt in world.rotation else pattern
                if nxt in world.shape:
                    if newpattern not in shape_edges:
                        continue  # unknown transition: learn it through real exploration
                    newpattern = shape_edges[newpattern]
                newcolor = (ci+1)%len(COLOR_CYCLE) if nxt in world.color else ci
                lock=goal_locations.get(nxt)
                if lock:
                    if (newpattern != lock.pattern or
                        COLOR_CYCLE[newcolor] != lock.color):
                        continue
                end=(nxt,newpattern,newcolor,newmask,after_meter)
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

    @staticmethod
    def _route_with_observed_transitions(
        start:tuple[int,int], goal:tuple[int,int], walkable:frozenset[tuple[int,int]],
        redirects:dict[tuple[tuple[int,int],str],tuple[int,int]],
        launchers:dict[tuple[int,int],tuple[int,int]],
        doors:set[tuple[int,int]]
    ) -> list[str] | None:
        if start == goal:
            return []
        q=deque([start])
        visited={start}
        parents={}
        while q:
            pos=q.popleft()
            for dx,dy,act in _MOVES:
                nominal=(pos[0]+dx,pos[1]+dy)
                dest=redirects.get((pos,act),nominal)
                if dest==nominal and nominal in walkable:
                    dest=LS20SearchPlanner._apply_launch(
                        nominal,walkable,doors,launchers)
                if dest==pos or dest not in walkable or dest in visited:
                    continue
                visited.add(dest)
                parents[dest]=(pos,act)
                if dest==goal:
                    route=[]
                    at=dest
                    while at!=start:
                        before,mv=parents[at]
                        route.append(mv)
                        at=before
                    return list(reversed(route))
                q.append(dest)
        return None

    def decide(self, serialized: str, level: int, allowed: set[str]) -> dict[str,Any]:
        self.searches+=1
        world=self.perceive(serialized,level)
        if world is None:
            return {"action":None,"policy":"ls20-search-v1",
                    "reason":"visual_perception_failed"}
        # Learn observed movement rules (including collisions and launch pads).
        # Never assume the environment obeyed a planned transition.
        if self.last_action is not None:
            last_level,from_pos,last_move,last_shape,previous_meter=self.last_action
            if last_level==level:
                transitions=self.observed_transitions.setdefault(level,{})
                expected={a:(from_pos[0]+dx,from_pos[1]+dy)
                          for dx,dy,a in _MOVES}.get(last_move)
                # Loss of a life respawns the avatar and restores the meter;
                # it is NOT a launcher edge. Refills are also non-teleport.
                reset=(world.meter_units>previous_meter and
                       world.key_shape==last_shape and
                       world.player!=expected)
                if world.player!=expected and not reset:
                    transitions[(from_pos,last_move)]=world.player
                if world.player in world.shape and world.player!=from_pos:
                    if world.key_shape!=last_shape:
                        self.learned_shapes.setdefault(level,{})[last_shape]=world.key_shape
            self.last_action=None
        overrides=self.observed_transitions.setdefault(level,{})
        learned=self.learned_shapes.setdefault(level,{})
        recent=self.recent_positions.setdefault(level,deque(maxlen=16))
        recent.append(world.player)
        route,stats=self.search(world,overrides,learned)
        self.last_stats=stats
        if route:
            action=route[0]
            if action not in allowed:
                return {"action":None,"policy":"ls20-search-v1",
                        "reason":"invalid_search_action"}
            self.last_action=(level,world.player,action,world.key_shape,world.meter_units)
            return {
                "action":{"action_type":action},
                "reason":"resource_constrained_search",
                "policy":"ls20-search-v1",
                "route_len":len(route),
                "position":world.player,
                "objective":route[-1],
                "meter_units":world.meter_units,
                "search_stats":{**stats,"visible_launchers":len(world.launches)},
            }
        # Fallback is explicitly tagged; it cannot be claimed as a solved plan.
        self.fallbacks+=1
        out=self.visual.decide(serialized,level,allowed)
        objective=out.get("objective")
        if isinstance(objective, (tuple,list)) and len(objective)==2:
            path=self._route_with_observed_transitions(
                world.player,tuple(objective),world.walkable,overrides,
                world.launches,{(door.x,door.y) for door in world.door})
            if path:
                out["action"]={"action_type":path[0]}
                out["route_len"]=len(path)
                out["reason"]="launch_aware_route_for_"+str(out.get("reason"))
            elif out.get("action") is not None:
                # No route to the current visual goal. Prevent replaying a
                # known collision/teleport cycle without new evidence.
                action=out["action"].get("action_type")
                if (world.player,action) in overrides:
                    candidates=[]
                    for dx,dy,other in _MOVES:
                        if other not in allowed:
                            continue
                        dest=overrides.get((world.player,other),
                                           (world.player[0]+dx,world.player[1]+dy))
                        if dest in world.walkable and dest!=world.player:
                            candidates.append(other)
                    if candidates:
                        alternative=[act for act in candidates if act!=action]
                        if alternative:
                            out["action"]={"action_type":alternative[0]}
                            out["reason"]="explore_alternative_after_observed_transition"
        # The public fifth level contains mobile modifiers/launchers. When the
        # observable avatar oscillates, avoid another move into the same
        # immediately visited state and probe a genuinely new exit direction.
        if level >= 4 and recent.count(world.player) >= 3:
            selected_action=(out.get("action") or {}).get("action_type")
            goal=out.get("objective")
            def rank(act:str):
                delta=next(((dx,dy) for dx,dy,name in _MOVES if name==act),(0,0))
                dest=overrides.get((world.player,act),
                                   (world.player[0]+delta[0],world.player[1]+delta[1]))
                distance=(abs(dest[0]-goal[0])+abs(dest[1]-goal[1])) if (
                    isinstance(goal,(tuple,list)) and len(goal)==2) else 0
                return (recent.count(dest),distance,act)
            choices=[]
            for dx,dy,act in _MOVES:
                if act not in allowed:
                    continue
                dest=overrides.get((world.player,act),
                                   (world.player[0]+dx,world.player[1]+dy))
                if dest in world.walkable and dest!=world.player:
                    choices.append(act)
            if choices:
                best=min(choices,key=rank)
                if best!=selected_action:
                    out["action"]={"action_type":best}
                    out["reason"]="escape_observed_oscillation"
        selected=out.get("action")
        if isinstance(selected,dict) and selected.get("action_type") in allowed:
            self.last_action=(level,world.player,selected["action_type"],world.key_shape,world.meter_units)
        out["policy"]="ls20-search-v1-fallback"
        out["search_stats"]={**stats,"known_teleports_or_blocks":len(overrides),
                              "learned_shape_transitions":len(learned)}
        return out
