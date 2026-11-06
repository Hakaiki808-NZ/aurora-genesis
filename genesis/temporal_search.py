"""Bounded time-dependent visual-state search for Genesis.

No environment source or hidden game variables. Uses only the public frame
parser's map and a separate world model's evidence-supported mover forecasts.
Every chosen action remains subject to real-environment validation.

This is a task-specific experimental search policy, not general AGI.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .visual_navigation import _MOVES, _rotate_clockwise


@dataclass(frozen=True)
class TemporalPlan:
    actions: tuple[str, ...]
    expanded: int
    visited: int
    goal_mask: int
    horizon: int
    model: str = "observed_periodic_movers"


def search_temporal(
    world: Any,
    learned_shapes: Mapping[tuple, tuple],
    forecasts: Mapping[str, Sequence[tuple[int, int]]],
    *,
    color_cycle: tuple[int, ...],
    horizon: int = 70,
    max_nodes: int = 130_000,
    target_mask: int | None = None,
    overrides: Mapping[tuple[tuple[int,int],str],tuple[int,int]] | None = None,
) -> tuple[TemporalPlan | None, dict[str, Any]]:
    """BFS in position, key state, consumed resources, goals and action time.

    The planner does not assume a moving modifier will remain where it was
    most recently seen. Contact is checked at the projected action timestep,
    and the caller must verify the predicted transition after each live move.
    """
    if not world.door or world.key_color not in color_cycle:
        return None, {"reason": "unknown_goal_or_color"}
    if not 1 <= horizon <= 100:
        raise ValueError("horizon must be within 1..100")
    if not forecasts:
        return None, {"reason": "no_evidence_backed_motion"}
    if len(world.energy)>8:
        return None, {"reason": "too_many_resources"}
    if any(len(sequence)<horizon for sequence in forecasts.values()):
        return None, {"reason": "forecast_shorter_than_horizon"}
    # All doors remain collision barriers, even when pursuing only one.
    doors={(obj.x,obj.y):(i,obj) for i,obj in enumerate(world.door)}
    allmask=(1<<len(world.door))-1
    if target_mask is None:
        target_mask=allmask
    if target_mask<1 or (target_mask&~allmask):
        return None, {"reason": "invalid_goal_mask"}
    goals=set(doors)
    resources={point:1<<i for i,point in enumerate(world.energy)}
    redirects=overrides or {}
    walkable=world.walkable
    start=(world.player,world.key_shape,color_cycle.index(world.key_color),
           0,world.meter_units,0,0)
    if start[4] < 0:
        return None, {"reason": "no_remaining_energy"}
    q=deque([start])
    parent:dict[tuple,tuple[tuple,str]]={}
    seen={start}
    # Dominance is valid only for identical observed temporal phase, action
    # count and resource state; keep all phases separate for moving sprites.
    best_meter={}
    expanded=0
    blocked_unknown_shape=0

    def apply_launcher(cell:tuple[int,int]) -> tuple[int,int]:
        delta=world.launches.get(cell)
        if delta is None:
            return cell
        x,y=cell
        for _ in range(12):
            dest=(x+delta[0],y+delta[1])
            if dest not in walkable or dest in goals:
                break
            x,y=dest
        return x,y

    for t in range(horizon):
        count=len(q)
        if count==0 or expanded>=max_nodes:
            break
        for _ in range(count):
            state=q.popleft()
            pos,shape,ci,mask,meter,open_doors,time=state
            if time!=t:
                continue
            expanded+=1
            for dx,dy,action in _MOVES:
                proposed=(pos[0]+dx,pos[1]+dy)
                nxt=redirects.get((pos,action),proposed)
                if nxt==proposed and proposed in walkable:
                    nxt=apply_launcher(proposed)
                if nxt==pos or nxt not in walkable:
                    continue

                remaining=meter-world.unit_cost
                picked=resources.get(nxt,0)
                resource_mask=mask
                if picked and not (mask&picked):
                    remaining=42
                    resource_mask|=picked
                if remaining<0:
                    continue

                # When the event order is not yet known, model endpoint
                # contact only; unexpected key changes invalidate plans
                # on the next frame, rather than silently assuming success.
                point_for=lambda kind,current: (
                    forecasts[kind][t] if kind in forecasts else current
                )
                rot=point_for("rotation",next(iter(world.rotation),None))
                shaper=point_for("shape",next(iter(world.shape),None))
                col=point_for("color",next(iter(world.color),None))

                transformed=shape
                if nxt == rot:
                    transformed=_rotate_clockwise(transformed)
                if nxt == shaper:
                    next_shape=learned_shapes.get(transformed)
                    if next_shape is None:
                        blocked_unknown_shape+=1
                        continue
                    transformed=next_shape
                next_ci=(ci+1)%len(color_cycle) if nxt==col else ci

                newdoors=open_doors
                if nxt in doors:
                    index,door=doors[nxt]
                    if door.pattern!=transformed or door.color!=color_cycle[next_ci]:
                        continue
                    newdoors|=(1<<index)

                after=(nxt,transformed,next_ci,resource_mask,
                       remaining,newdoors,t+1)
                if after in seen:
                    continue
                signature=(nxt,transformed,next_ci,resource_mask,newdoors,t+1)
                if best_meter.get(signature,-1)>=remaining:
                    continue
                best_meter[signature]=remaining
                seen.add(after)
                parent[after]=(state,action)
                if (newdoors&target_mask)==target_mask:
                    moves=[]
                    cursor=after
                    while cursor!=start:
                        previous,move=parent[cursor]
                        moves.append(move)
                        cursor=previous
                    moves.reverse()
                    plan=TemporalPlan(tuple(moves),expanded,len(seen),target_mask,horizon)
                    return plan,{
                        "reason":"time_expanded_goal_search",
                        "length":len(moves),"expanded":expanded,
                        "visited":len(seen),"goal_mask":target_mask,
                        "unknown_shape_edges_blocked":blocked_unknown_shape,
                        "world_models":sorted(forecasts),
                    }
                q.append(after)
            if expanded>=max_nodes:
                break
    return None,{
        "reason":"no_temporal_goal_path",
        "expanded":expanded,"visited":len(seen),
        "cap_hit":expanded>=max_nodes,
        "unknown_shape_edges_blocked":blocked_unknown_shape,
        "world_models":sorted(forecasts)
    }
