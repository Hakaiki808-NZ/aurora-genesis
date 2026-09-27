from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field

class GeneratorBackend:
    name="none"
    def available(self)->bool: return False
    def generate(self,prompt:str)->str|None: return None

@dataclass
class OllamaBackend(GeneratorBackend):
    model: str="qwen2.5-coder:1.5b"
    base_url: str="http://127.0.0.1:11434"
    timeout: float=0.35
    name:str="ollama"
    _checked: bool=field(default=False,init=False,repr=False)
    _available: bool=field(default=False,init=False,repr=False)

    def available(self)->bool:
        if self._checked:return self._available
        self._checked=True
        try:
            with urllib.request.urlopen(self.base_url+"/api/tags",timeout=self.timeout) as r:
                data=json.loads(r.read().decode("utf-8")); names=[m.get("name") or m.get("model") for m in data.get("models",[])]
            names=[n for n in names if n]
            if self.model=="auto" and names:self.model=names[0]
            self._available=bool(names) and self.model in names
        except Exception:self._available=False
        return self._available

    def generate(self,prompt:str)->str|None:
        if not self.available():return None
        payload=json.dumps({"model":self.model,"prompt":prompt,"stream":False,"options":{"temperature":0.2}}).encode()
        req=urllib.request.Request(self.base_url+"/api/generate",data=payload,headers={"Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(req,timeout=45) as r:data=json.loads(r.read().decode())
            text=str(data.get("response","")).strip(); return text or None
        except Exception:return None
