from __future__ import annotations

import re
from typing import Any

from .storage import Store
from .tools import ToolRegistry


class Planner:
    """Goal planner/executor for bounded autonomous work cycles."""
    def __init__(self, store: Store, tools: ToolRegistry):
        self.store=store; self.tools=tools

    def plan(self, goal: str) -> list[dict[str,Any]]:
        g=goal.strip()
        low=g.casefold()
        # Concrete plans for capabilities the engine can really execute.
        m=re.search(r"(?i)(?:learn from|ingest)\s+file\s+([\w.\-/]+)$",g)
        if m:
            return [{"description":f"Ingest knowledge from {m.group(1)}","action":"ingest","args":{"path":m.group(1)}}]
        m=re.search(r"(?i)^use\s+skill\s+(.+)$",g)
        if m:
            skill=self.store.skill(m.group(1).strip())
            if skill:return skill["steps"]
        m=re.search(r"(?i)(?:calculate|compute)\s+(.+)$",g)
        if m:
            expr=m.group(1).strip().rstrip(".?")
            return [{"description":f"Calculate {expr}","action":"tool","args":{"name":"calculate","expression":expr}}]
        m=re.search(r"(?i)(?:write|save)\s+(?:a\s+)?note\s+(?:called\s+)?([\w.\-/]+)\s+(?:saying|with|containing)\s+(.+)$",g)
        if m:
            return [{"description":f"Write note {m.group(1)}","action":"tool","args":{"name":"write_note","path":m.group(1),"text":m.group(2)}}]
        if "summar" in low:
            return [{"description":"Retrieve relevant stored knowledge","action":"internal","args":{"operation":"retrieve","query":g}}, {"description":"Synthesize retrieved knowledge","action":"internal","args":{"operation":"summarize","query":g}}]
        return [{"description":"Inspect relevant knowledge and determine what is known","action":"internal","args":{"operation":"retrieve","query":g}}, {"description":"Produce the best current answer or explicitly identify missing knowledge","action":"internal","args":{"operation":"answer","query":g}}]

    def create(self, goal: str, priority: int=50) -> int:
        gid=self.store.create_goal(goal,priority)
        self.store.set_goal_steps(gid,self.plan(goal))
        return gid
