from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from .storage import Store, norm

_TOKEN=re.compile(r"[a-z0-9][a-z0-9_\-']+", re.I)
_STOP={"the","a","an","is","are","was","were","be","been","being","what","who","where","when","why","how","do","does","did","you","your","my","i","it","this","that","of","to","in","on","for","and","or","about","know","remember","tell","me"}


def tokens(text: str) -> list[str]:
    return [t.casefold() for t in _TOKEN.findall(text) if t.casefold() not in _STOP]


class Retriever:
    """Transparent BM25-style retriever with revision-aware document caching."""
    def __init__(self, store: Store):
        self.store=store
        self._revision_token: tuple[int,str] | None=None
        self._snapshots: dict[str|None,tuple[list[dict[str,Any]],list[Counter],Counter,float]]={}

    def _snapshot(self, namespace: str | None):
        token=self.store.fact_revision_token()
        if token!=self._revision_token:
            self._revision_token=token
            self._snapshots.clear()
        if namespace in self._snapshots:
            return self._snapshots[namespace]
        facts=self.store.all_facts(namespace)
        if not facts:
            snap=([],[],Counter(),0.0); self._snapshots[namespace]=snap; return snap
        docs=[tokens(f["key"]+" "+f["value"]) for f in facts]
        tfs=[Counter(d) for d in docs]
        N=len(docs); avgdl=sum(map(len,docs))/max(1,N)
        df=Counter()
        for d in docs:
            for term in set(d): df[term]+=1
        snap=(facts,tfs,df,avgdl)
        self._snapshots[namespace]=snap
        return snap

    def search(self, query: str, limit: int=8, namespace: str | None=None) -> list[dict[str,Any]]:
        facts,tfs,df,avgdl=self._snapshot(namespace)
        if not facts: return []
        q=tokens(query)
        if not q: return []
        N=len(facts); out=[]; k1=1.5; b=0.75; nq=norm(query)
        for fact,tf in zip(facts,tfs):
            doclen=sum(tf.values()); score=0.0
            for term in q:
                freq=tf.get(term,0)
                if not freq: continue
                idf=math.log(1+(N-df[term]+0.5)/(df[term]+0.5))
                denom=freq+k1*(1-b+b*doclen/max(avgdl,1e-9))
                score += idf*(freq*(k1+1))/denom
            if fact["key_norm"]==nq: score += 20.0
            elif fact["key_norm"] in nq or nq in fact["key_norm"]: score += 4.0
            score *= max(0.1,float(fact["confidence"]))
            if score>0:
                hit=dict(fact); hit["score"]=score; out.append(hit)
        out.sort(key=lambda x:(x["score"],x["confidence"],x["updated_at"]), reverse=True)
        return out[:limit]
