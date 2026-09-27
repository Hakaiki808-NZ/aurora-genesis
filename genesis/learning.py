from __future__ import annotations
import re
from typing import Any
from .reasoning import Reasoner
from .storage import Store

class Learner:
    def __init__(self,store:Store,reasoner:Reasoner):self.store=store;self.reasoner=reasoner
    @staticmethod
    def sentences(text:str)->list[str]:return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+",text) if s.strip()]
    def from_input(self,text:str,source:str="interaction",truth_state:str="ASSERTED",source_trust:str="trusted")->list[dict[str,Any]]:
        learned=[]
        for sentence in self.sentences(text):
            m=re.match(r"(?is)^(?:learn\s+that\s+|remember\s+that\s+)?when\s+(?:i\s+say|you\s+hear)\s+[\"']?(.+?)[\"']?\s*,\s*(?:reply|respond|answer)(?:\s+with)?\s+[\"']?(.+?)[\"']?[.!]?$",sentence)
            if m and source_trust=="trusted":
                learned.append(self.store.learn_response_rule(m.group(1).strip(),m.group(2).strip().rstrip(".!?"),source=sentence));continue
            m=re.match(r"(?is)^(?:learn|remember|note|store)(?:\s+that)?\s+(?:the\s+)?(.+?)\s+(?:is|are|means|equals)\s+(.+?)[.!]?$",sentence)
            if m:
                key=m.group(1).strip();value=m.group(2).strip().rstrip(".!?");ns="self" if key.casefold().startswith(("your ","aurora ")) else "world"
                learned.append(self.store.learn_fact(key,value,namespace=ns,source=source if source!="interaction" else sentence,truth_state=truth_state))
                tri=self.reasoner.parse_declarative(f"{key} is {value}")
                if tri:self.store.add_triple(*tri,source=source if source!="interaction" else sentence)
                continue
            if source_trust=="trusted":
                m=re.match(r"(?is)^(?:i\s+)?prefer\s+(.+?)(?:\s+over\s+(.+?))?[.!]?$",sentence)
                if m:learned.append(self.store.learn_fact("preferred option",m.group(1).strip(),namespace="preference",source=sentence));continue
                m=re.match(r"(?is)^(?:avoid|do not choose|never choose)\s+(.+?)[.!]?$",sentence)
                if m:
                    value=m.group(1).strip();learned.append(self.store.learn_fact(f"avoid option {value}",value,namespace="constraint",source=sentence));continue
            if "?" not in sentence and not re.match(r"(?i)^(choose|tell|show|give|do|can|could|would|please|set goal|run goal|calculate|compute|ingest|use skill|learn skill)\b",sentence):
                m=re.match(r"(?is)^\s*(?:the\s+|my\s+)?(.+?)\s+(is|are|means|equals)\s+(.+?)[.!]?\s*$",sentence)
                if m:
                    key=m.group(1).strip();verb=m.group(2).casefold();raw_value=m.group(3).strip().rstrip(".!?");value=re.sub(r"(?i)^(?:a|an)\s+","",raw_value).strip()
                    if len(key)<=100 and len(value)<=240 and key.casefold() not in {"i","you","this","that","it"}:
                        learned.append(self.store.learn_fact(key,value,namespace="world",confidence=0.9,source=source if source!="interaction" else sentence,truth_state=truth_state))
                        if verb=="are" or bool(re.match(r"(?i)^(?:a|an)\s+",raw_value)):learned.append(self.store.add_triple(key,"is a",value,confidence=0.9,source=source if source!="interaction" else sentence))
                        continue
                tri=self.reasoner.parse_declarative(sentence)
                if tri and len(tri[0])<=100 and len(tri[2])<=240:learned.append(self.store.add_triple(*tri,confidence=0.9,source=source if source!="interaction" else sentence))
        return learned
    def from_untrusted_text(self,text:str,source:str="untrusted document")->list[dict[str,Any]]:
        return self.from_input(text,source=source,truth_state="ASSERTED",source_trust="untrusted")
