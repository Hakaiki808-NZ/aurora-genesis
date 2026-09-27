from __future__ import annotations

import ast
import operator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .types import ToolResult


class ToolError(RuntimeError):
    pass


class SafeCalculator:
    """Small arithmetic evaluator with explicit complexity/resource bounds."""

    OPS={
        ast.Add:operator.add, ast.Sub:operator.sub, ast.Mult:operator.mul,
        ast.Div:operator.truediv, ast.FloorDiv:operator.floordiv,
        ast.Mod:operator.mod, ast.Pow:operator.pow,
        ast.USub:operator.neg, ast.UAdd:operator.pos,
    }
    MAX_EXPR_CHARS=256
    MAX_NODES=64
    MAX_ABS_RESULT=10**100

    @classmethod
    def eval(cls, expr: str) -> float | int:
        if not isinstance(expr,str) or not expr.strip():
            raise ToolError("empty expression")
        if len(expr)>cls.MAX_EXPR_CHARS:
            raise ToolError("expression too long")
        try:
            node=ast.parse(expr,mode="eval")
        except (SyntaxError,ValueError) as e:
            raise ToolError("invalid expression") from e
        if sum(1 for _ in ast.walk(node))>cls.MAX_NODES:
            raise ToolError("expression too complex")

        def bounded(value):
            if isinstance(value,(int,float)) and abs(value)>cls.MAX_ABS_RESULT:
                raise ToolError("result magnitude too large")
            return value

        def walk(n):
            if isinstance(n,ast.Expression):
                return walk(n.body)
            if isinstance(n,ast.Constant) and isinstance(n.value,(int,float)) and not isinstance(n.value,bool):
                return bounded(n.value)
            if isinstance(n,ast.UnaryOp) and type(n.op) in cls.OPS:
                return bounded(cls.OPS[type(n.op)](walk(n.operand)))
            if isinstance(n,ast.BinOp) and type(n.op) in cls.OPS:
                a,b=walk(n.left),walk(n.right)
                if isinstance(n.op,ast.Pow):
                    if abs(b)>12:
                        raise ToolError("exponent too large")
                    if abs(a)>10**12:
                        raise ToolError("power base too large")
                try:
                    return bounded(cls.OPS[type(n.op)](a,b))
                except ZeroDivisionError as e:
                    raise ToolError("division by zero") from e
            raise ToolError("unsupported expression")
        return walk(node)


@dataclass
class ToolSpec:
    name: str
    description: str
    fn: Callable[...,Any]
    mutating: bool=False
    policy_flags: tuple[str,...]=()
    external_side_effect: bool=False
    irreversible: bool=False
    sensitive_data: bool=False
    policy_declared: bool=False


class ToolRegistry:
    """Bounded capability registry designed to sit behind a future UI permission layer."""

    MAX_READ_BYTES=1_000_000
    MAX_WRITE_BYTES=1_000_000
    MAX_LIST_FILES=5000

    def __init__(self, workspace: str | Path):
        self.workspace=Path(workspace).expanduser().resolve()
        self.workspace.mkdir(parents=True,exist_ok=True)
        self._tools: dict[str,ToolSpec]={}
        self.register("calculate","Evaluate bounded arithmetic safely",lambda expression: SafeCalculator.eval(expression),policy_flags=())
        self.register("read_text","Read a UTF-8 text file inside the AURORA workspace",self._read_text,policy_flags=())
        self.register("write_note","Write a UTF-8 note inside the AURORA workspace",self._write_note,mutating=True,policy_flags=("bounded_local_mutation",),policy_declared=True)
        self.register("list_workspace","List workspace files with a bounded result set",self._list_workspace,policy_flags=())

    def register(self,name:str,description:str,fn:Callable[...,Any],mutating:bool=False,*,policy_flags:tuple[str,...]|list[str]=(),external_side_effect:bool=False,irreversible:bool=False,sensitive_data:bool=False,policy_declared:bool=False)->None:
        if not name or not isinstance(name,str):
            raise ValueError("tool name must be non-empty")
        self._tools[name]=ToolSpec(name,description,fn,mutating,tuple(policy_flags),bool(external_side_effect),bool(irreversible),bool(sensitive_data),bool(policy_declared))

    def _resolve(self,relative_path:str)->Path:
        if not isinstance(relative_path,str) or not relative_path.strip():
            raise ToolError("path must be non-empty")
        p=(self.workspace/relative_path).resolve()
        if self.workspace!=p and self.workspace not in p.parents:
            raise ToolError("path escapes workspace")
        return p

    def _read_text(self,path:str)->str:
        p=self._resolve(path)
        if not p.exists() or not p.is_file():
            raise ToolError("file not found")
        if p.stat().st_size>self.MAX_READ_BYTES:
            raise ToolError("file exceeds 1 MB read limit")
        try:
            return p.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            raise ToolError("file is not valid UTF-8 text") from e

    def _write_note(self,path:str,text:str)->dict[str,Any]:
        if not isinstance(text,str):
            text=str(text)
        size=len(text.encode("utf-8"))
        if size>self.MAX_WRITE_BYTES:
            raise ToolError("write exceeds 1 MB limit")
        p=self._resolve(path)
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(text,encoding="utf-8")
        return {"path":str(p.relative_to(self.workspace)),"bytes":size}

    def _list_workspace(self)->list[str]:
        out=[]
        for p in sorted(self.workspace.rglob('*')):
            if p.is_file():
                out.append(str(p.relative_to(self.workspace)))
                if len(out)>=self.MAX_LIST_FILES:
                    break
        return out

    def specs(self)->list[dict[str,Any]]:
        return [{"name":s.name,"description":s.description,"mutating":s.mutating,"policy_flags":list(s.policy_flags),"external_side_effect":s.external_side_effect,"irreversible":s.irreversible,"sensitive_data":s.sensitive_data,"policy_declared":s.policy_declared} for s in self._tools.values()]

    def spec(self,name:str)->ToolSpec|None:
        return self._tools.get(name)

    def has(self,name:str)->bool:
        return name in self._tools

    def call(self,name:str,**kwargs)->ToolResult:
        spec=self._tools.get(name)
        if not spec:
            return ToolResult(False,name,error="unknown tool")
        try:
            return ToolResult(True,name,output=spec.fn(**kwargs))
        except Exception as e:
            return ToolResult(False,name,error=f"{type(e).__name__}: {e}")
