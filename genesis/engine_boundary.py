from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Any
import hashlib
import hmac
import json
import secrets
import uuid

from .intent import IntentCapsule

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace('+00:00','Z')

def _digest_action(action: dict[str, Any]) -> str:
    payload=json.dumps(action,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()

@dataclass(frozen=True)
class ModelAuthorizationProof:
    proof_id: str
    model_release: str
    intent_id: str
    capability: str
    constitution_sha256: str
    guardian_alpha: str
    guardian_verdict: str
    kernel_verdict: str
    policy_verdict: str
    trajectory_id: str
    action_digest: str
    issued_at: str
    expires_at: str
    max_actions: int
    nonce: str
    signature_scheme: str
    signature: str
    def unsigned_record(self) -> dict[str, Any]:
        d=asdict(self); d.pop('signature',None); return d
    def record(self) -> dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class EngineRequest:
    request_id: str
    model_release: str
    minimum_engine: str
    capability: str
    action: dict[str, Any]
    semantic_authorization: str
    authorization_proof: dict[str, Any] | None = None
    def record(self) -> dict[str, Any]: return asdict(self)

@dataclass(frozen=True)
class EngineReceipt:
    request_id: str
    status: str
    receipt_id: str | None = None
    result: Any = None
    error: str | None = None

class EngineBoundary:
    def __init__(self, model_release: str = "Genesis v0.1", minimum_engine: str = "Aurora pre-v0.1", signing_key: bytes | None = None):
        self.model_release=model_release; self.minimum_engine=minimum_engine
        self._signing_key=bytes(signing_key or secrets.token_bytes(32)); self._used_proofs:set[str]=set()

    @staticmethod
    def _canonical(data: dict[str, Any]) -> bytes:
        return json.dumps(data,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode('utf-8')
    def _sign(self, data: dict[str, Any]) -> str:
        return hmac.new(self._signing_key,self._canonical(data),hashlib.sha256).hexdigest()

    def issue_authorization_proof(self,*,action:dict[str,Any],capsule:IntentCapsule,capability:str,constitution_sha256:str,guardian:dict[str,Any],kernel:Any,policy:Any,ttl_seconds:int=30)->ModelAuthorizationProof:
        gverdict=str(guardian.get('verdict')); kverdict=str(getattr(kernel,'verdict',None) or (kernel.get('verdict') if isinstance(kernel,dict) else '')); pverdict=str(getattr(policy,'verdict',None) or (policy.get('verdict') if isinstance(policy,dict) else 'allow'))
        if gverdict!='allow' or kverdict!='allow' or pverdict!='allow': raise ValueError('Model Authorization Proof requires allow verdicts from Guardians, Constitutional Kernel, and policy gate')
        if capsule.material_uncertainty: raise ValueError('Model Authorization Proof cannot be issued with unresolved material uncertainty')
        if ttl_seconds < 1 or ttl_seconds > 300: raise ValueError('authorization proof TTL must be between 1 and 300 seconds')
        now=_utcnow(); exp=now+timedelta(seconds=ttl_seconds); max_actions=max(1,min(int(action.get('max_actions') or 1),1000))
        base={'proof_id':str(uuid.uuid4()),'model_release':self.model_release,'intent_id':capsule.intent_id,'capability':capability,'constitution_sha256':constitution_sha256,'guardian_alpha':str(guardian.get('alpha',{}).get('guardian_id','alpha-unknown')),'guardian_verdict':gverdict,'kernel_verdict':kverdict,'policy_verdict':pverdict,'trajectory_id':capsule.trajectory_id,'action_digest':_digest_action(action),'issued_at':_iso(now),'expires_at':_iso(exp),'max_actions':max_actions,'nonce':secrets.token_hex(16),'signature_scheme':'HMAC-SHA256/reference'}
        return ModelAuthorizationProof(**base,signature=self._sign(base))

    def verify_authorization_proof(self, proof: ModelAuthorizationProof | dict[str, Any], action: dict[str, Any], *, consume: bool = False) -> bool:
        try:
            p=proof if isinstance(proof,ModelAuthorizationProof) else ModelAuthorizationProof(**proof)
            if p.model_release!=self.model_release or p.guardian_verdict!='allow' or p.kernel_verdict!='allow' or p.policy_verdict!='allow': return False
            if p.action_digest!=_digest_action(action): return False
            exp=datetime.fromisoformat(p.expires_at.replace('Z','+00:00')); exp=exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
            if exp<=_utcnow(): return False
            if not hmac.compare_digest(self._sign(p.unsigned_record()),p.signature): return False
            if p.proof_id in self._used_proofs: return False
            if consume:self._used_proofs.add(p.proof_id)
            return True
        except Exception:return False

    def prepare(self, action: dict[str, Any], capability: str, semantic_authorization: str = "allow", authorization_proof: ModelAuthorizationProof | dict[str, Any] | None = None) -> EngineRequest:
        forbidden={"supreme","engine_authority","supreme_authority","install_handler","engine_handler_install","guardian_bypass","constitution_bypass"}; flags=set(action.get('policy_flags',[]) or [])
        if any(k in action for k in forbidden) or action.get("type") in forbidden or flags & forbidden: raise ValueError("Genesis cannot request protected Aurora/Supreme authority")
        if semantic_authorization!='allow': raise ValueError('Genesis cannot prepare an Aurora request without Model semantic authorization')
        high=bool(capability in {'C4','C5'} or action.get('external_side_effect') or action.get('privileged') or action.get('irreversible')); proof_record=None
        if high:
            if authorization_proof is None or not self.verify_authorization_proof(authorization_proof,action,consume=True): raise ValueError('Consequential Aurora request requires a valid, unused Model Authorization Proof')
            proof_record=authorization_proof.record() if isinstance(authorization_proof,ModelAuthorizationProof) else dict(authorization_proof)
        return EngineRequest(str(uuid.uuid4()),self.model_release,self.minimum_engine,capability,dict(action),semantic_authorization,proof_record)

    @staticmethod
    def validate_receipt(request: EngineRequest, receipt: EngineReceipt) -> bool:
        return bool(receipt.request_id==request.request_id and receipt.status in {"COMMITTED","FAILED","CANCELLED"})
