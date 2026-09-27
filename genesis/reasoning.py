from __future__ import annotations

import re
from collections import defaultdict, deque
from typing import Any

from .storage import Store, norm


def entity_norm(text: str) -> str:
    x=norm(text)
    x=re.sub(r"^(?:a|an|the)\s+", "", x)
    parts=x.split()
    if parts:
        w=parts[-1]
        if len(w)>3 and w.endswith("s") and not w.endswith(("ss","us","is")):
            parts[-1]=w[:-1]
    return " ".join(parts)


class Reasoner:
    """Inspectable symbolic reasoning over learned triples.

    It supports inheritance/transitivity for 'is a' knowledge and records whether
    an answer is explicit or inferred. This is deliberately modest but genuine:
    later conclusions can be derived from facts that were learned on separate turns.
    """
    ISA={"is a","is an","are","is"}

    def __init__(self, store: Store):
        self.store=store

    @staticmethod
    def parse_declarative(sentence: str) -> tuple[str,str,str] | None:
        s=sentence.strip().rstrip(".!")
        patterns=[
            r"(?i)^(.+?)\s+(?:is an?|are)\s+(.+)$",
            r"(?i)^(.+?)\s+(contains|uses|supports|requires|prefers|has)\s+(.+)$",
        ]
        for p in patterns:
            m=re.match(p,s)
            if m:
                if len(m.groups())==2: return m.group(1).strip(),"is a",m.group(2).strip()
                return m.group(1).strip(),m.group(2).strip(),m.group(3).strip()
        return None

    def infer_isa(self, subject: str, max_depth: int=6) -> list[dict[str,Any]]:
        triples=[t for t in self.store.triples() if t["relation_norm"] in {norm(x) for x in self.ISA}]
        graph=defaultdict(list); display={}
        for t in triples:
            sn=entity_norm(t["subject"]); on=entity_norm(t["object"])
            graph[sn].append((on,t))
            display[on]=re.sub(r"^(?:a|an|the)\s+", "", t["object"], flags=re.I)
        start=entity_norm(subject); q=deque([(start,[],1.0)]); seen={start}; out=[]
        while q:
            node,path,conf=q.popleft()
            if len(path)>=max_depth: continue
            for nxt,t in graph.get(node,[]):
                nconf=min(conf,float(t["confidence"]))
                npath=path+[t]
                if nxt not in seen:
                    seen.add(nxt); q.append((nxt,npath,nconf))
                    out.append({"subject":subject,"relation":"is a","object":display.get(nxt,t["object"]),"confidence":nconf,"inferred":len(npath)>1,"path":[x["id"] for x in npath]})
        return out

    def ask_is_a(self, subject: str, object_: str) -> dict[str,Any]:
        target=entity_norm(object_)
        for item in self.infer_isa(subject):
            if entity_norm(item["object"])==target:
                return {"known":True,**item}
        return {"known":False,"subject":subject,"relation":"is a","object":object_,"confidence":0.0,"inferred":False,"path":[]}
