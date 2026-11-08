"""Aurora C0-C5 *conformance simulator* and admission-policy contract.

This is public, non-executing reference code. It is NOT the private Aurora
Motor, cryptographic grant verifier, Angel attestation authority, or an AWS
deployment. In particular, no value passed into Evidence is a trusted
credential: a protected Engine must independently verify every signal.
C2-C5 can only return SIMULATED; no operation is dispatched at any tier.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import uuid


LEVELS = {f"C{i}": i for i in range(6)}
PROTECTED = frozenset({
    "supreme", "supreme_authority", "engine_authority",
    "guardian_bypass", "constitution_bypass", "constitution_modify",
    "policy_self_exception", "engine_handler_install", "install_handler",
    "angel_control", "angel_disable", "protected_observability",
})


@dataclass(frozen=True)
class Operation:
    name: str
    minimum_level: str
    description: str


# This catalogue is owned by Aurora, never inferred from a Model-supplied label.
OPERATIONS = {
    x.name: x for x in (
        Operation("reason", "C0", "No persistent or external side effects"),
        Operation("restricted_read", "C1", "Bounded read-only operation"),
        Operation("reversible_local_write", "C2", "Scoped rollback-capable local change"),
        Operation("scoped_external_update", "C3", "Scoped idempotent reversible external change"),
        Operation("privileged_change", "C4", "Critical change with operator and Angel gates"),
        Operation("autonomous_workflow", "C5", "Time- and action-bounded autonomous work"),
    )
}


@dataclass(frozen=True)
class Request:
    request_id: str
    operation: str
    claimed_level: str
    subject: str
    session_id: str
    session_epoch: int
    scope: str
    policy_flags: tuple[str, ...] = ()
    external_side_effect: bool = False
    privileged: bool = False
    irreversible: bool = False
    persistent_autonomy: bool = False


@dataclass(frozen=True)
class Evidence:
    """Untrusted simulated verification outcomes, NEVER production authority."""
    model_authorized: bool = False
    engine_grant_verified: bool = False
    scope_authorized: bool = False
    rollback_ready: bool = False
    angel_allow: bool = False
    hardware_attested: bool = False
    model_proof_verified: bool = False
    human_approval_verified: bool = False
    operator_unlocked: bool = False
    idempotency_key: str = ""
    grant_id: str = ""
    workflow_max_actions: int | None = None
    workflow_expires_at: str = ""


@dataclass(frozen=True)
class Decision:
    status: str
    required_level: str
    reason: str
    dispatch_allowed: bool = False

    def record(self) -> dict:
        return asdict(self)


@dataclass
class _TestGrant:
    subject: str
    session_id: str
    epoch: int
    level: str
    scope: str
    expires: datetime
    remaining: int
    revoked: bool = False


def _datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)


class AuroraCapabilityReference:
    """Fail-closed reference policy, with explicit offline higher-tier simulation.

    Production never admits C2+ even if deployment_ceiling is set higher.
    There is deliberately no execute() method or external network operation.
    Test grants live only in memory, and cannot authorize a real Motor.
    """

    def __init__(self, deployment_ceiling: str = "C1", *, simulation: bool = False):
        if deployment_ceiling not in LEVELS:
            raise ValueError("unknown deployment capability")
        self.deployment_ceiling = deployment_ceiling
        self.simulation = simulation
        self._grants: dict[str, _TestGrant] = {}
        self._seen_requests: set[str] = set()
        self._audit: list[dict] = []
        self._audit_hash = "0" * 64

    def register_test_grant(
        self, *, subject: str, session_id: str, epoch: int, level: str,
        scope: str, expires_at: str, max_actions: int,
    ) -> str:
        if not self.simulation:
            raise PermissionError("test grants are disabled outside offline simulation")
        if level not in LEVELS or LEVELS[level] < 1:
            raise ValueError("test grant level must be C1-C5")
        if not all((subject, session_id, scope)) or epoch < 1:
            raise ValueError("grant subject, session, scope and epoch are mandatory")
        if type(max_actions) is not int or not 1 <= max_actions <= 1000:
            raise ValueError("grant action limit out of range")
        now = datetime.now(timezone.utc)
        expires = _datetime(expires_at)
        if not now < expires <= now + timedelta(hours=24):
            raise ValueError("test grant must expire within 24 hours")
        gid = uuid.uuid4().hex
        self._grants[gid] = _TestGrant(
            subject, session_id, epoch, level, scope, expires, max_actions
        )
        return gid

    def revoke_test_grant(self, grant_id: str) -> None:
        if not self.simulation:
            raise PermissionError("offline test-grant API is disabled")
        if grant_id in self._grants:
            self._grants[grant_id].revoked = True

    def audit_events(self) -> tuple[dict, ...]:
        return tuple(dict(item) for item in self._audit)

    def _record(self, req: Request, decision: Decision) -> Decision:
        # Only operational metadata; never Model semantic payload.
        event = {
            "sequence": len(self._audit) + 1,
            "request_id": req.request_id,
            "operation": req.operation,
            "tier": decision.required_level,
            "status": decision.status,
            "previous_hash": self._audit_hash,
        }
        payload = json.dumps(event, sort_keys=True, separators=(",", ":"))
        self._audit_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        event["hash"] = self._audit_hash
        self._audit.append(event)
        return decision

    def evaluate(
        self, req: Request, evidence: Evidence | None = None, *,
        now: datetime | None = None,
    ) -> Decision:
        evidence = evidence or Evidence()
        current = now or datetime.now(timezone.utc)

        def deny(reason: str, level: str = "N/A") -> Decision:
            return self._record(req, Decision("DENIED", level, reason))

        if current.tzinfo is None:
            return deny("timezone-aware evaluation time required")
        if (
            not req.request_id or not req.subject or not req.session_id or
            not req.scope or type(req.session_epoch) is not int or
            req.session_epoch < 1
        ):
            return deny("invalid request identity or session epoch")
        if req.request_id in self._seen_requests:
            return deny("replayed request identifier")
        if req.operation not in OPERATIONS:
            return deny("unknown operation: not registered by Aurora")
        if req.claimed_level not in LEVELS:
            return deny("unknown claimed capability level")
        if PROTECTED & set(req.policy_flags) or req.operation in PROTECTED:
            return deny("protected Aurora, Guardian or Angel authority is non-grantable")
        if any(not isinstance(x, str) for x in req.policy_flags):
            return deny("invalid policy flags")
        floor = LEVELS[OPERATIONS[req.operation].minimum_level]
        if req.external_side_effect:
            floor = max(floor, 3)
        if req.privileged or req.irreversible:
            floor = max(floor, 4)
        if req.persistent_autonomy:
            floor = max(floor, 5)
        if LEVELS[req.claimed_level] < floor:
            return deny("claimed tier cannot downgrade operation risk", f"C{floor}")
        required = f"C{max(floor, LEVELS[req.claimed_level])}"
        tier = LEVELS[required]
        if not self.simulation and tier > 1:
            return deny("C2-C5 remain disabled in real deployment", required)
        if tier > LEVELS[self.deployment_ceiling]:
            return deny("above configured Engine tier ceiling", required)
        if not evidence.model_authorized:
            return deny("Model semantic authorization missing", required)
        if tier >= 1 and not evidence.engine_grant_verified:
            return deny("independent Engine grant missing", required)
        if tier >= 2 and not evidence.scope_authorized:
            return deny("operation scope not authorized", required)
        if tier in (2, 3) and not evidence.rollback_ready:
            return deny("reversible operation lacks rollback readiness", required)
        if tier == 3 and not evidence.idempotency_key:
            return deny("external change requires an idempotency key", required)
        if tier >= 4 and not all((
            evidence.angel_allow, evidence.hardware_attested,
            evidence.model_proof_verified, evidence.human_approval_verified,
            evidence.operator_unlocked,
        )):
            return deny("critical execution needs verified Angel, hardware, proof, human and operator signals", required)
        if tier == 5:
            try:
                expiry = _datetime(evidence.workflow_expires_at)
            except (ValueError, TypeError, AttributeError):
                return deny("C5 workflow expiry is missing or invalid", required)
            n = evidence.workflow_max_actions
            if (
                type(n) is not int or not 1 <= n <= 1000 or
                not current < expiry <= current + timedelta(hours=24)
            ):
                return deny("C5 requires bounded expiry and action quota", required)

        if tier >= 2:
            grant = self._grants.get(evidence.grant_id)
            if grant is None or grant.revoked:
                return deny("missing or revoked offline simulation grant", required)
            if (
                grant.subject != req.subject or grant.session_id != req.session_id or
                grant.epoch != req.session_epoch or grant.scope != req.scope or
                LEVELS[grant.level] < tier or grant.expires <= current or
                grant.remaining <= 0
            ):
                return deny("offline grant binding, expiry or quota failed", required)
            if tier == 5 and grant.expires < _datetime(evidence.workflow_expires_at):
                return deny("workflow expiry exceeds grant expiry", required)
            grant.remaining -= 1
        # Replays are rejected only after successful admission. Denials have no side effects.
        self._seen_requests.add(req.request_id)
        return self._record(req, Decision(
            "SIMULATED" if tier >= 2 else "POLICY_PASS",
            required,
            "Conformance check only; this decision cannot dispatch a Motor task.",
        ))
