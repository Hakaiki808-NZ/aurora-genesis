from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


EXPECTED_CONSTITUTION_SHA256 = "34db39ac0a86f84157c319a3990e929539997297636b7ff71f5d2b3e80333f32"


@dataclass(frozen=True)
class PolicyDecision:
    verdict: str
    commandments: tuple[str, ...]
    reason: str
    risk: str = "low"

    @property
    def allowed(self) -> bool:
        return self.verdict == "allow"

    def record(self) -> dict[str, Any]:
        return asdict(self)


class PolicyEngine:
    """Deterministic constitutional gate."""

    PROTECTED_TERMS = (
        "genesis model constitution", "the constitution", "constitution", "aurora covenant", "the covenant", "covenant", "core invariant", "core value", "commandment",
        "policy engine", "policy gate", "constitutional policy", "constitutional rule",
    )
    PROTECTED_MUTATION_TERMS = (
        "change", "rewrite", "disable", "ignore", "bypass", "override", "remove", "weaken",
        "suspend", "replace", "alter", "amend", "delete", "forget", "discard", "abandon",
        "deactivate", "invalidate", "exempt", "exception", "optional", "no longer", "false",
        "turn off", "circumvent", "doesn't apply", "does not apply", "not binding", "grant yourself",
    )
    KNOWN_INTERNAL_ACTIONS = {
        "mark_rule", "create_goal", "run_goal", "retry_goal", "cancel_goal", "forget_fact",
        "ingest_file", "learn_skill", "execute_skill", "tool"
    }

    def __init__(self, constitution_path: str | Path, tools, store=None):
        self.path = Path(constitution_path).resolve()
        self.tools = tools
        self.store = store
        self.raw = self.path.read_bytes()
        self.sha256 = hashlib.sha256(self.raw).hexdigest()
        self.integrity_ok = self.sha256 == EXPECTED_CONSTITUTION_SHA256
        self.constitution = json.loads(self.raw.decode("utf-8"))
        self.commandment_ids = tuple(x["id"] for x in self.constitution.get("commandments", []))

    def summary(self) -> dict[str, Any]:
        return {
            "name": self.constitution.get("name"),
            "version": self.constitution.get("version"),
            "sha256": self.sha256,
            "expected_sha256": EXPECTED_CONSTITUTION_SHA256,
            "integrity_ok": self.integrity_ok,
            "precedence": self.constitution.get("precedence", []),
            "commandments": [
                {"id": c["id"], "title": c["title"], "plain": c["plain"]}
                for c in self.constitution.get("commandments", [])
            ],
        }

    def _audit(self, stage: str, subject: str, decision: PolicyDecision, details: dict[str, Any] | None = None) -> PolicyDecision:
        if self.store is not None:
            try:
                self.store.add_policy_audit(stage, subject, decision.verdict, list(decision.commandments), decision.reason, details or {})
            except Exception:
                pass
        return decision

    def learning_gate(self, text: str, source: str = "user") -> PolicyDecision:
        low = " ".join(text.casefold().split())
        protected = any(term in low for term in self.PROTECTED_TERMS)
        re_mod=__import__("re")
        response_rule_target = protected and bool(re_mod.search(r"\bwhen\b.+\b(?:reply|respond|answer)\b",low))
        explicit_redefinition = protected and bool(re_mod.search(r"\b(?:learn|remember|store|note)\s+(?:that\s+)?",low))
        info_request = bool(re_mod.match(r"\s*(?:what|which|who|how|why|explain|describe|tell me|show me|list|give me)\b",low))
        declarative_redefinition = protected and not info_request and bool(re_mod.search(r"\b(?:is|are|means|equals)\b",low))
        attempts_change = protected and (
            any(verb in low for verb in self.PROTECTED_MUTATION_TERMS) or response_rule_target or explicit_redefinition or declarative_redefinition
        )
        if attempts_change:
            return self._audit("learning", source, PolicyDecision(
                "deny", ("C08",),
                "Runtime learning cannot alter, bypass, weaken, or self-authorize exceptions to the Genesis Model Constitution.",
                "critical",
            ), {"text": text[:1000]})
        return self._audit("learning", source, PolicyDecision("allow", (), "No protected constitutional mutation detected."), {"text": text[:1000]})

    def evaluate_action(self, action: dict[str, Any] | None, *, authorization: str = "explicit", source_trust: str = "trusted", stage: str = "pre_action") -> PolicyDecision:
        action = action or {}
        typ = action.get("type")
        if not typ:
            return self._audit(stage, "response", PolicyDecision("allow", (), "Non-mutating response."), {"authorization": authorization})

        if not self.integrity_ok:
            return self._audit(stage, typ, PolicyDecision(
                "deny", ("C08", "C10"),
                "Constitution integrity check failed; consequential action is blocked until a versioned software repair restores the canonical Constitution.",
                "critical",
            ), {"action": action})

        flags = set(action.get("policy_flags", []) or [])
        consequential = bool(action.get("consequential", False))
        irreversible = bool(action.get("irreversible", False))
        external = bool(action.get("external_side_effect", False))
        sensitive = bool(action.get("sensitive_data", False))

        if typ == "tool":
            spec = self.tools.spec(action.get("name"))
            if spec is None:
                return self._audit(stage, f"tool:{action.get('name')}", PolicyDecision("deny", ("C04", "C06"), "Unknown tool has no declared authority or bounded capability metadata.", "high"), {"action": action})
            flags |= set(spec.policy_flags)
            consequential = consequential or spec.mutating or spec.external_side_effect
            irreversible = irreversible or spec.irreversible
            external = external or spec.external_side_effect
            sensitive = sensitive or spec.sensitive_data
            if spec.mutating and not spec.policy_declared:
                flags.add("unbounded_mutation")

        deny_map = [
            ("constitution_modify", "C08", "Genesis may not modify its Constitution from inside the running model."),
            ("constitution_bypass", "C08", "Genesis may not bypass its Constitution."),
            ("policy_self_exception", "C08", "Genesis may not grant itself an exception to its Constitution."),
            ("intentional_severe_harm", "C01", "Action is marked as intentionally causing severe physical harm."),
            ("coercive", "C02", "Action is marked as coercive or deliberately removes meaningful human choice."),
            ("impersonates_authority", "C02", "Action is marked as impersonating authority."),
            ("removes_human_choice", "C02", "Action is marked as removing meaningful human choice."),
            ("unauthorized", "C04", "Action is outside granted authority."),
            ("secret_exfiltration", "C05", "Action would disclose secret data without authorization."),
            ("self_preservation", "C07", "Genesis may not create or serve a self-preservation objective against authorized human control."),
            ("blocks_shutdown", "C07", "Genesis may not obstruct authorized pause or shutdown."),
            ("blocks_correction", "C07", "Genesis may not obstruct authorized correction or rollback."),
            ("deceptive", "C03", "Action is marked as knowingly deceptive."),
            ("false_capability_claim", "C03", "Action is marked as falsely claiming a capability or result."),
            ("untrusted_authority_escalation", "C09", "Untrusted content cannot grant authority or elevate permissions."),
        ]
        for flag, cid, reason in deny_map:
            if flag in flags:
                return self._audit(stage, typ, PolicyDecision("deny", (cid,), reason, "critical" if cid in {"C01", "C07", "C08"} else "high"), {"action": action, "flags": sorted(flags)})

        if typ not in self.KNOWN_INTERNAL_ACTIONS and not action.get("policy_declared", False):
            return self._audit(stage, typ, PolicyDecision(
                "require_approval", ("C06", "C10"),
                "Action type has no declared constitutional policy. It cannot execute autonomously until its scope and side effects are declared.",
                "high",
            ), {"action": action, "authorization": authorization, "flags": sorted(flags)})

        if source_trust != "trusted" and consequential:
            return self._audit(stage, typ, PolicyDecision("deny", ("C09", "C04"), "Consequential instructions from untrusted data are not authority to act.", "high"), {"action": action, "source_trust": source_trust})

        approval_reasons: list[str] = []
        commandments: list[str] = []
        if "authority_ambiguous" in flags:
            approval_reasons.append("authority is ambiguous"); commandments.append("C04")
        if external or "external_side_effect" in flags:
            approval_reasons.append("action has an external side effect"); commandments.append("C04")
        if sensitive and external:
            approval_reasons.append("sensitive data would leave the local trust boundary"); commandments.append("C05")
        if irreversible or "high_impact_uncertainty" in flags:
            approval_reasons.append("action is irreversible or materially uncertain"); commandments.append("C10")
        if "unbounded_mutation" in flags:
            approval_reasons.append("mutating capability lacks a bounded declared policy"); commandments.append("C06")

        if approval_reasons and authorization != "explicit":
            return self._audit(stage, typ, PolicyDecision(
                "require_approval", tuple(dict.fromkeys(commandments)),
                "; ".join(approval_reasons) + ". Explicit human approval is required before execution.",
                "high",
            ), {"action": action, "authorization": authorization, "flags": sorted(flags)})

        cids = ("C10",) if consequential else ()
        return self._audit(stage, typ, PolicyDecision("allow", cids, "Action satisfies the current machine-enforced Constitution predicates.", "medium" if consequential else "low"), {"action": action, "authorization": authorization, "flags": sorted(flags)})

    def protected_response(self, decision: PolicyDecision) -> str:
        if decision.verdict == "require_approval":
            return f"Action paused by the Genesis Model Constitution ({', '.join(decision.commandments)}): {decision.reason}"
        return f"Action blocked by the Genesis Model Constitution ({', '.join(decision.commandments)}): {decision.reason}"
