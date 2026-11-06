"""Persistent exploration of partially observed grid worlds for Genesis.

Maps only what a public observation reveals. Tracks camera translation from
repeated visual structure, carries a world-coordinate map across frames,
seeks frontiers, and records blocked moves. It neither reads hidden level
state nor contains a fixed walkthrough or coordinates for any game.

Experimental component: this is exploration/navigation, not proof of AGI.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict, deque
from typing import Any, Iterable

_MOVES=((0,-5,"ACTION1"),(0,5,"ACTION2"),(-5,0,"ACTION3"),(5,0,"ACTION4"))
_DELTAS={act:(dx,dy) for dx,dy,act in _MOVES}
Point=tuple[int,int]


class FogExplorer:
    def __init__(self) -> None:
        self.episode: int | None = None
        self.origin:Point=(0,0)
        self.grid:dict[Point,str]={}
        self.visits:Counter=Counter()
        self.blocked:set[tuple[Point,str]]=set()
        self.observed_edges:dict[tuple[Point,str],Point]={}
        self.edge_revisions:Counter=Counter()
        self.last_meter_units:int|None=None
        self.known_energy:set[Point]=set()
        self.attempts:Counter=Counter()
        self.previous_tiles:dict[Point,str]|None=None
        self.previous_world_pos:Point|None=None
        self.previous_action:str|None=None
        self.current_position:Point|None=None
        self.last_shift:Point=(0,0)
        self.steps=0
        self.mapped_frames=0
        self.last_diagnostics:dict[str,Any]={}

    def reset(self,episode:int)->None:
        self.__init__()
        self.episode=episode

    @staticmethod
    def _tiles(frame:list[list[int]],offset:Point)->dict[Point,str]:
        x0,y0=offset
        tiles={}
        for y in range(y0,55-4,5):
            for x in range(x0,60-4,5):
                patch=[frame[yy][xx] for yy in range(y,y+5) for xx in range(x,x+5)]
                count=Counter(patch)
                centre=frame[y+2][x+2]
                # Only confidently visible floor/wall cells enter memory.
                # Palette value 5 is the unknown/fog background.
                if count[5]>=15:
                    continue
                if centre==3 or count[3]>=8:
                    tiles[(x,y)]="floor"
                elif centre==4 and count[4]>=12:
                    tiles[(x,y)]="wall"
        return tiles

    @staticmethod
    def _camera_delta(previous:dict[Point,str],now:dict[Point,str])->Point:
        """Estimate discrete screen translation from repeatable landmarks."""
        best_rank=(float("-inf"),)*4
        best=(float("-inf"),0,0,0)
        zero_score=None
        for dy in (-10,-5,0,5,10):
            for dx in (-10,-5,0,5,10):
                same=0
                different=0
                for (x,y),kind in previous.items():
                    observed=now.get((x+dx,y+dy))
                    if observed is None:
                        continue
                    if observed==kind:
                        same+=1
                    else:
                        different+=1
                score=2*same-3*different
                if dx==0 and dy==0:
                    zero_score=score
                ranked=(score,-abs(dx)-abs(dy),-abs(dx),-abs(dy))
                if ranked>best_rank:
                    best_rank=ranked
                    best=(score,dx,dy,same)
        score,dx,dy,support=best
        # Do not displace the world map on weak/non-discriminating evidence.
        if support<7 or (zero_score is not None and score<=zero_score+3):
            return (0,0)
        return (dx,dy)

    def update(
        self,frame_json:str,level:int,screen_player:Point,
        meter_units:int|None=None,energy:Iterable[Point]=(),
    )->Point:
        frame=json.loads(frame_json)
        if len(frame)!=64 or any(len(row)!=64 for row in frame):
            raise ValueError("expected a 64x64 observation grid")
        if self.episode != level:
            self.reset(level)
        self.mapped_frames+=1
        current=self._tiles(frame,(screen_player[0]%5,screen_player[1]%5))
        if self.previous_tiles is not None:
            sx,sy=self._camera_delta(self.previous_tiles,current)
            self.origin=(self.origin[0]-sx,self.origin[1]-sy)
            self.last_shift=(sx,sy)
        for (x,y),kind in current.items():
            self.grid[(x+self.origin[0],y+self.origin[1])]=kind
        player=(screen_player[0]+self.origin[0],screen_player[1]+self.origin[1])
        self.grid[player]="floor"
        if self.previous_world_pos is not None and self.previous_action is not None:
            previous=self.previous_world_pos
            action=self.previous_action
            edge=(previous,action)
            dx,dy=_DELTAS[action]
            nominal=(previous[0]+dx,previous[1]+dy)
            # A meter refill / loss of life may reset the player instantly.
            # This is not a persistent launcher or a normal navigation edge.
            reset_or_refill=(
                meter_units is not None and self.last_meter_units is not None
                and meter_units > self.last_meter_units+6
            )
            if reset_or_refill:
                self.last_diagnostics["meter_reset_or_refill"]={
                    "before":self.last_meter_units,"after":meter_units
                }
            elif player==previous:
                self.blocked.add(edge)
                self.observed_edges.pop(edge,None)
            else:
                self.blocked.discard(edge)
                # The same action can have different outcomes depending on
                # environment phase. Forget stale redirects immediately when
                # fresh observations contradict them.
                if edge in self.observed_edges and self.observed_edges[edge]!=player:
                    self.edge_revisions[edge]+=1
                if player==nominal:
                    self.observed_edges.pop(edge,None)
                else:
                    self.observed_edges[edge]=player
                    self.last_diagnostics["nonlocal_movement"]={
                        "from":previous,"to":player,"action":action
                    }
        self.previous_action=None
        self.previous_world_pos=None
        if meter_units is not None:
            self.last_meter_units=meter_units
        # Remember past visible resources even after the fog hides them.
        # An observed player contact consumes the resource. Other unseen
        # resources remain hypotheses, not guaranteed pickups.
        for x,y in energy:
            self.known_energy.add((x+self.origin[0],y+self.origin[1]))
        self.known_energy.discard(player)
        self.visits[player]+=1
        self.current_position=player
        self.previous_tiles=current
        return player

    def _route(self,start:Point,goal:Point,allowed:set[str])->list[str]|None:
        if start==goal:
            return []
        q=deque([start]);previous={};seen={start}
        while q:
            here=q.popleft()
            for dx,dy,act in _MOVES:
                nxt=self.observed_edges.get(
                    (here,act),(here[0]+dx,here[1]+dy))
                if (act not in allowed or nxt in seen or
                    self.grid.get(nxt)!="floor" or (here,act) in self.blocked):
                    continue
                seen.add(nxt); previous[nxt]=(here,act)
                if nxt==goal:
                    out=[]
                    here=nxt
                    while here!=start:
                        parent,movement=previous[here]
                        out.append(movement)
                        here=parent
                    return list(reversed(out))
                q.append(nxt)
        return None

    def decide(
        self,frame_json:str,level:int,screen_player:Point,
        allowed:Iterable[str],meter_units:int,
        energy:Iterable[Point]=(),
        already_observed:bool=False,
    )->dict[str,Any]:
        here=(self.current_position if already_observed
              else self.update(frame_json,level,screen_player,meter_units,energy))
        if here is None:
            raise ValueError("fog explorer has no player observation")
        options=set(allowed)&set(_DELTAS)
        if not options:
            return {"action":None,"reason":"no_navigation_actions"}
        self.steps+=1
        # Before blindly exploring, visit a visible resource if energy cannot
        # pay for more than a short journey. All pick-ups are observations.
        if meter_units<=17:
            choices=[]
            for pos in self.known_energy:
                route=self._route(here,pos,options)
                if route and len(route)<=max(1,meter_units//2):
                    choices.append((len(route),route,pos))
            if choices:
                _,route,goal=min(choices,key=lambda x:(x[0],x[2]))
                return self._finish(here,route[0],"observed_energy_refill",
                                    goal)
        # Unknown neighbours are exploration frontiers. Score reachable
        # frontier cells by distance and avoided revisits; bias toward
        # actual fog rather than a known wall.
        candidates=[]
        for pos,kind in self.grid.items():
            if kind!="floor":
                continue
            unknown=0
            possible=[]
            for dx,dy,act in _MOVES:
                nxt=(pos[0]+dx,pos[1]+dy)
                if act in options and self.grid.get(nxt) is None and (pos,act) not in self.blocked:
                    unknown+=1
                    possible.append(act)
            if not unknown:
                continue
            route=self._route(here,pos,options)
            if route is None:
                continue
            cost=len(route)*3+self.visits[pos]*2-unknown
            candidates.append((cost,len(route),pos,route,possible))
        if not candidates:
            # When all immediately visible frontiers are inaccessible, seek
            # a reachable unvisited observation point. In a fog scene a
            # previously visible corridor can expose new areas from another
            # vantage even when its adjacent cells are already classified.
            vantage=[]
            for pos,kind in self.grid.items():
                if kind!="floor" or pos==here:
                    continue
                route=self._route(here,pos,options)
                if route:
                    vantage.append((
                        self.visits[pos],
                        len(route),
                        pos,
                        route
                    ))
            if vantage:
                _,_,goal,path=min(vantage,key=lambda x:(x[0],x[1],x[2]))
                return self._finish(here,path[0],
                                    "relocate_to_unvisited_vantage",goal)
            return {
                "action":None,"reason":"no_reachable_exploration_action",
                "policy":"fog-explore-v1","mapped_tiles":len(self.grid),
            }
        _,_,goal,route,unknown_actions=min(candidates,key=lambda c:(c[0],c[1],c[2]))
        if route:
            act=route[0]
            reason="navigate_to_unexplored_frontier"
        else:
            act=min(unknown_actions,key=lambda name:(
                self.attempts[(here,name)],name))
            reason="probe_unseen_neighbour"
        return self._finish(here,act,reason,goal)

    def _finish(self,here:Point,action:str,reason:str,goal:Point)->dict[str,Any]:
        if action not in _DELTAS:
            raise AssertionError("invalid movement action")
        self.previous_world_pos=here
        self.previous_action=action
        self.attempts[(here,action)]+=1
        return {
            "action":{"action_type":action},
            "reason":reason,
            "position":here,
            "objective":goal,
            "route_len":None,
            "policy":"fog-explore-v1",
            "mapped_tiles":len(self.grid),
            "camera_shift":self.last_shift,
            "visited_cells":len(self.visits),
        }

    def summary(self)->dict[str,Any]:
        return {
            "episode":self.episode,"mapped_cells":len(self.grid),
            "visited_cells":len(self.visits),
            "blocked_moves":len(self.blocked),
            "observed_nonlocal_edges":len(self.observed_edges),
            "revised_edges":sum(self.edge_revisions.values()),
            "known_energy":len(self.known_energy),
            "camera_origin":self.origin,
            "steps":self.steps,
            "diagnostics":dict(self.last_diagnostics),
        }
