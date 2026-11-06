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
        # Shape-tile mechanics transfer across levels. This is learned ONLY
        # when actual observations show a shape change after tile contact.
        self.global_shape_edges:dict[tuple[tuple[int,...],...],tuple[tuple[int,...],...]] = {}
        self.recent_positions:dict[int,deque[tuple[int,int]]] = {}
        self.modifier_history:dict[tuple[int,str],deque[tuple[int,int]]] = {}

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
        start=(world.player, world.key_shape, COLOR_CYCLE.index(world.key_color),
               0, world.meter_units, 0)
        queue=deque([start])
        visited={start}
        # Dominance: for identical map/key/door/pickup state, extra energy
        # can only make more continuations possible.  Keep the maximum
        # meter reached for that abstract state, avoiding 42 near-identical
        # copies of many branches.
        def abstract(state):
            pos, pattern, ci, pickups, meter, doors = state
            return (pos, pattern, ci, pickups, doors)
        best_meter = {abstract(start):start[4]}
        dominated = 0
        parents:dict[tuple,tuple[tuple,str]]={}
        energy_bit={point:1<<i for i,point in enumerate(world.energy)}
        goal_locations={(o.x,o.y):(idx,o) for idx,o in enumerate(world.door)}
        goal_points=set(goal_locations)
        all_doors=(1<<len(world.door))-1
        expanded=0
        while queue and expanded < MAX_NODES:
            state=queue.popleft()
            expanded+=1
            (x,y),pattern,ci,mask,meter,door_mask=state
            if meter < best_meter.get(abstract(state), -1):
                dominated += 1
                continue
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
                new_door_mask=door_mask
                if lock:
                    door_id,door=lock
                    if not (door_mask & (1<<door_id)):
                        if (newpattern != door.pattern or
                            COLOR_CYCLE[newcolor] != door.color):
                            continue
                        new_door_mask |= 1<<door_id
                end=(nxt,newpattern,newcolor,newmask,after_meter,new_door_mask)
                if end in visited:
                    continue
                key=abstract(end)
                if best_meter.get(key,-1) >= after_meter:
                    dominated += 1
                    continue
                best_meter[key]=after_meter
                visited.add(end)
                parents[end]=(state,action)
                if new_door_mask==all_doors:
                    route=[]
                    cur=end
                    while cur!=start:
                        parent,mv=parents[cur]
                        route.append(mv)
                        cur=parent
                    route.reverse()
                    return route, {"reason":"solved_symbolic_search",
                                   "expanded":expanded,"visited":len(visited),
                                   "length":len(route),"refills_modelled":len(world.energy),
                                   "doors_modelled":len(world.door),
                                   "known_shape_transitions":len(shape_edges),
                                   "pruned_dominated":dominated}
                queue.append(end)
        return None, {"reason":"no_goal_path_found",
                      "expanded":expanded,"visited":len(visited),
                      "reached_cap":expanded>=MAX_NODES,
                      "refills_modelled":len(world.energy),
                      "pruned_dominated":dominated,
                      "abstract_states":len(best_meter)}

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

    @staticmethod
    def _forecast_mover(history: list[tuple[int,int]], horizon:int) -> list[tuple[int,int]]:
        """Predict positions from only observed motion, never hidden game state.

        Prefer a previously observed recurring two-state suffix; otherwise
        extrapolate a recent linear velocity and reflect at observed bounds.
        These predictions are uncertain and revised on every observation.
        """
        if not history:
            return []
        seq=list(history)
        forecast=[seq[-1]]
        for _ in range(horizon):
            nxt=None
            if len(seq)>=3:
                a,b=seq[-2:]
                # A matching pair in earlier observations yields an empirical
                # successor, handling reversals and short patrol loops.
                for i in range(len(seq)-3,-1,-1):
                    if seq[i:i+2]==[a,b] and i+2<len(seq):
                        nxt=seq[i+2]
                        break
            if nxt is None and len(seq)>=2:
                x,y=seq[-1]; px,py=seq[-2]
                dx,dy=x-px,y-py
                if abs(dx)+abs(dy)==5:
                    xs=[p[0] for p in history]
                    ys=[p[1] for p in history]
                    nx,ny=x+dx,y+dy
                    if len(history)>=5:
                        if nx<min(xs) or nx>max(xs): nx=x-dx
                        if ny<min(ys) or ny>max(ys): ny=y-dy
                    nxt=(nx,ny)
            if nxt is None:
                nxt=seq[-1]
            forecast.append(nxt)
            seq.append(nxt)
        return forecast

    @staticmethod
    def _moving_intercept(
        world:SearchWorld,
        positions:list[tuple[int,int]],
        allowed:set[str],
        overrides:dict[tuple[tuple[int,int],str],tuple[int,int]],
        horizon:int=16,
    ) -> list[str] | None:
        """Time-expanded navigation to a predicted moving modifier.

        A cell is sampled on entry; the target moves on player actions.
        Search includes current action timestep and observed launcher edges.
        """
        if not positions:
            return None
        starts=(world.player,0)
        q=deque([starts])
        parents={}
        seen={starts}
        doors={(d.x,d.y) for d in world.door}
        while q:
            (x,y),t=q.popleft()
            if t>=horizon:
                continue
            for dx,dy,act in _MOVES:
                if act not in allowed:
                    continue
                nominal=(x+dx,y+dy)
                landing=overrides.get(((x,y),act),nominal)
                if landing==nominal and nominal in world.walkable:
                    landing=LS20SearchPlanner._apply_launch(
                        nominal,world.walkable,doors,world.launches)
                if landing not in world.walkable or landing==(x,y):
                    continue
                next_state=(landing,t+1)
                if next_state in seen:
                    continue
                seen.add(next_state)
                parents[next_state]=((x,y),t,act)
                expected=positions[min(t,len(positions)-1)]
                if landing == expected:
                    route=[]
                    current=next_state
                    while current!=starts:
                        parent_pos,parent_t,mv=parents[current]
                        route.append(mv)
                        current=(parent_pos,parent_t)
                    return list(reversed(route))
                q.append(next_state)
        return None

    def decide(self, serialized: str, level: int, allowed: set[str]) -> dict[str,Any]:
        self.searches+=1
        world=self.perceive(serialized,level)
        if world is None:
            return {"action":None,"policy":"ls20-search-v1",
                    "reason":"visual_perception_failed"}
        # Track movable modifiers independently per level, using only frame
        # observations; this history drives a time-expanded intercept search.
        for kind,points in (("shape",world.shape),("color",world.color),
                            ("rotation",world.rotation)):
            if len(points)==1:
                hist=self.modifier_history.setdefault((level,kind),
                                                        deque(maxlen=40))
                hist.append(next(iter(points)))
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
                # Moving modifiers can vacate the cell before the new frame
                # is emitted.  Learn from the visible key transition itself.
                # Reject pure quarter-turn rotation and life resets.
                if (world.key_shape != last_shape and
                    world.key_shape != _rotate_clockwise(last_shape) and
                    not reset):
                    self.learned_shapes.setdefault(level,{})[last_shape]=world.key_shape
                    self.global_shape_edges[last_shape]=world.key_shape
            self.last_action=None
        overrides=self.observed_transitions.setdefault(level,{})
        learned=self.learned_shapes.setdefault(level,{})
        learned.update(self.global_shape_edges)
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
        # An unknown shape-cycle operation blocks a complete model-based
        # solution. Gather one REAL observed transition at the visible shape
        # tile instead of cycling colours first or fabricating the result.
        if level >= 4 and world.shape and world.door:
            wanted={obj.pattern for obj in world.door}
            orientations={world.key_shape}
            current_shape=world.key_shape
            for _ in range(3):
                current_shape=_rotate_clockwise(current_shape)
                orientations.add(current_shape)
            shape_needed=not (orientations & wanted)
            # Also learn the shape transition when the current shape has no
            # observed successor.  Level six contains *two* lock targets;
            # being able to match one of them is insufficient reason to
            # stop learning the general shape cycle.
            unseen_shape_transition = world.key_shape not in learned
            if shape_needed or unseen_shape_transition:
                shape_candidates=[]
                for dest in world.shape:
                    path=self._route_with_observed_transitions(
                        world.player,dest,world.walkable,overrides,
                        world.launches,{(d.x,d.y) for d in world.door})
                    if path is not None:
                        shape_candidates.append((len(path),dest,path))
                if shape_candidates:
                    shape_candidates.sort()
                    _,chosen,route_to_shape=shape_candidates[0]
                    if not route_to_shape:
                        # Re-entering the same modifier is the only way to
                        # discover more of its unknown shape permutation.
                        departures=[]
                        for dx,dy,action in _MOVES:
                            if action not in allowed: continue
                            nominal=(world.player[0]+dx,world.player[1]+dy)
                            landing=overrides.get((world.player,action),nominal)
                            if landing==nominal and landing in world.walkable:
                                landing=self._apply_launch(
                                    nominal,world.walkable,
                                    {(d.x,d.y) for d in world.door},world.launches)
                            if landing==world.player or landing not in world.walkable:
                                continue
                            return_path=self._route_with_observed_transitions(
                                landing,chosen,world.walkable,overrides,
                                world.launches,{(d.x,d.y) for d in world.door})
                            if return_path:
                                departures.append((len(return_path),action))
                        if departures:
                            departures.sort()
                            route_to_shape=[departures[0][1]]
                    # The visible modifier can move each time we act.
                    # Intercept its predicted trajectory rather than chasing
                    # the tile at the point where it was last seen.
                    track=list(self.modifier_history.get((level,"shape"),()))
                    if len(track)>=3:
                        future=self._forecast_mover(track,16)
                        intercept=self._moving_intercept(
                            world,future,allowed,overrides,horizon=16)
                        if intercept:
                            route_to_shape=intercept
                    if route_to_shape:
                        selected=route_to_shape[0]
                        self.last_action=(level,world.player,selected,
                                          world.key_shape,world.meter_units)
                        return {"action":{"action_type":selected},
                                "reason":("intercept_moving_shape" if len(track)>=3 and intercept else
                                          "learn_unknown_shape_cycle"),
                                "policy":"ls20-visual-experiment",
                                "route_len":len(route_to_shape),
                                "objective":chosen,
                                "position":world.player,
                                "search_stats":{**stats,
                                                "shape_transition_samples":
                                                len(learned),
                                                "visible_launchers":
                                                len(world.launches)}}
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
