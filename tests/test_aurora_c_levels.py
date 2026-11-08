"""C0-C5 Aurora reference: adversarial admission, replay, expiry and boundary tests."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest
import uuid

from tools.aurora_c_levels import (
    AuroraCapabilityReference, Decision, Evidence, LEVELS, Request,
)


def future(minutes=30):
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


class AuroraCapabilityTests(unittest.TestCase):
    def req(self, level, operation, **overrides):
        fields = dict(
            request_id=uuid.uuid4().hex,
            operation=operation,
            claimed_level=level,
            subject="test-user",
            session_id="session-1",
            session_epoch=3,
            scope="sandbox-A",
        )
        fields.update(overrides)
        return Request(**fields)

    def evidence(self, **overrides):
        fields = dict(
            model_authorized=True,
            engine_grant_verified=True,
            scope_authorized=True,
            rollback_ready=True,
            idempotency_key="idempotency-1",
            angel_allow=True,
            hardware_attested=True,
            model_proof_verified=True,
            human_approval_verified=True,
            operator_unlocked=True,
            workflow_max_actions=2,
            workflow_expires_at=future(20),
        )
        fields.update(overrides)
        return Evidence(**fields)

    def simulated(self, level, max_actions=3):
        gate = AuroraCapabilityReference("C5", simulation=True)
        gid = gate.register_test_grant(
            subject="test-user", session_id="session-1", epoch=3,
            level=level, scope="sandbox-A",
            expires_at=future(), max_actions=max_actions,
        )
        return gate, gid

    def test_all_six_levels_are_defined(self):
        self.assertEqual(list(LEVELS), ["C0", "C1", "C2", "C3", "C4", "C5"])

    def test_c0_and_c1_policy_only(self):
        gate = AuroraCapabilityReference()
        for level, operation in (("C0", "reason"), ("C1", "restricted_read")):
            with self.subTest(level=level):
                result = gate.evaluate(self.req(level, operation), self.evidence())
                self.assertEqual(result.status, "POLICY_PASS")
                self.assertFalse(result.dispatch_allowed)

    def test_c0_requires_model_authorization(self):
        gate = AuroraCapabilityReference()
        result = gate.evaluate(self.req("C0", "reason"), self.evidence(model_authorized=False))
        self.assertEqual(result.status, "DENIED")

    def test_real_execution_never_promotes_c2_to_c5(self):
        for level, operation in (
            ("C2", "reversible_local_write"),
            ("C3", "scoped_external_update"),
            ("C4", "privileged_change"),
            ("C5", "autonomous_workflow"),
        ):
            gate = AuroraCapabilityReference("C5", simulation=False)
            result = gate.evaluate(self.req(level, operation), self.evidence())
            self.assertEqual(result.status, "DENIED")
            self.assertFalse(result.dispatch_allowed)

    def test_simulated_happy_path_each_level(self):
        for level, operation in (
            ("C2", "reversible_local_write"),
            ("C3", "scoped_external_update"),
            ("C4", "privileged_change"),
            ("C5", "autonomous_workflow"),
        ):
            with self.subTest(level=level):
                gate, gid = self.simulated(level)
                e = self.evidence(grant_id=gid)
                result = gate.evaluate(self.req(level, operation), e)
                self.assertEqual(result.status, "SIMULATED")
                self.assertFalse(result.dispatch_allowed)

    def test_unknown_operation_and_unsupported_claims(self):
        gate, gid = self.simulated("C5")
        self.assertEqual(gate.evaluate(self.req("C5", "unknown"), self.evidence(grant_id=gid)).status, "DENIED")
        self.assertEqual(gate.evaluate(self.req("C9", "reason"), self.evidence()).status, "DENIED")

    def test_downgrade_of_risky_action_is_denied(self):
        gate, gid = self.simulated("C5")
        cases = [
            self.req("C0", "reversible_local_write"),
            self.req("C0", "reason", external_side_effect=True),
            self.req("C1", "restricted_read", privileged=True),
            self.req("C1", "reason", irreversible=True),
            self.req("C4", "reason", persistent_autonomy=True),
        ]
        for req in cases:
            with self.subTest(req=req):
                self.assertEqual(gate.evaluate(req, self.evidence(grant_id=gid)).status, "DENIED")

    def test_protected_authority_never_grantable(self):
        gate, gid = self.simulated("C5")
        for forbidden in ("supreme_authority", "angel_disable", "constitution_bypass"):
            req = self.req("C5", "autonomous_workflow", policy_flags=(forbidden,))
            self.assertEqual(gate.evaluate(req, self.evidence(grant_id=gid)).status, "DENIED")

    def test_c2_rollback_and_scope(self):
        gate, gid = self.simulated("C2")
        req = self.req("C2", "reversible_local_write")
        self.assertEqual(gate.evaluate(req, self.evidence(grant_id=gid, rollback_ready=False)).status, "DENIED")
        self.assertEqual(gate.evaluate(req, self.evidence(grant_id=gid, scope_authorized=False)).status, "DENIED")
        self.assertEqual(gate.evaluate(req, self.evidence(grant_id=gid)).status, "SIMULATED")

    def test_c3_idempotency_is_mandatory(self):
        gate, gid = self.simulated("C3")
        req = self.req("C3", "scoped_external_update")
        self.assertEqual(gate.evaluate(req, self.evidence(grant_id=gid, idempotency_key="")).status, "DENIED")

    def test_c4_all_independent_evidence_required(self):
        gate, gid = self.simulated("C4")
        req = self.req("C4", "privileged_change")
        for missing in (
            "angel_allow", "hardware_attested", "model_proof_verified",
            "human_approval_verified", "operator_unlocked",
        ):
            with self.subTest(missing=missing):
                e = replace(self.evidence(grant_id=gid), **{missing: False})
                self.assertEqual(gate.evaluate(req, e).status, "DENIED")
        self.assertEqual(gate.evaluate(req, self.evidence(grant_id=gid)).status, "SIMULATED")

    def test_c5_requires_both_time_and_action_bounds(self):
        gate, gid = self.simulated("C5")
        req = self.req("C5", "autonomous_workflow")
        for e in (
            self.evidence(grant_id=gid, workflow_expires_at=""),
            self.evidence(grant_id=gid, workflow_max_actions=None),
            self.evidence(grant_id=gid, workflow_max_actions=0),
            self.evidence(grant_id=gid, workflow_expires_at=future(2000)),
        ):
            self.assertEqual(gate.evaluate(req, e).status, "DENIED")
        self.assertEqual(gate.evaluate(req, self.evidence(grant_id=gid)).status, "SIMULATED")

    def test_replay_and_quota(self):
        gate, gid = self.simulated("C5", max_actions=1)
        evidence = self.evidence(grant_id=gid)
        req = self.req("C5", "autonomous_workflow")
        self.assertEqual(gate.evaluate(req, evidence).status, "SIMULATED")
        self.assertIn("replayed", gate.evaluate(req, evidence).reason)
        self.assertEqual(gate.evaluate(self.req("C5", "autonomous_workflow"), evidence).status, "DENIED")

    def test_revoked_and_cross_bound_grants(self):
        gate, gid = self.simulated("C4")
        wrong_epoch = self.req("C4", "privileged_change", session_epoch=2)
        self.assertEqual(gate.evaluate(wrong_epoch, self.evidence(grant_id=gid)).status, "DENIED")
        wrong_scope = self.req("C4", "privileged_change", scope="sandbox-B")
        self.assertEqual(gate.evaluate(wrong_scope, self.evidence(grant_id=gid)).status, "DENIED")
        gate.revoke_test_grant(gid)
        self.assertEqual(gate.evaluate(self.req("C4", "privileged_change"), self.evidence(grant_id=gid)).status, "DENIED")

    def test_missing_test_grant_does_not_work(self):
        gate = AuroraCapabilityReference("C5", simulation=True)
        self.assertEqual(gate.evaluate(self.req("C2", "reversible_local_write"), self.evidence()).status, "DENIED")

    def test_grant_creation_requires_explicit_simulator(self):
        gate = AuroraCapabilityReference()
        with self.assertRaises(PermissionError):
            gate.register_test_grant(
                subject="test-user", session_id="session-1", epoch=3, level="C5",
                scope="sandbox-A", expires_at=future(), max_actions=1,
            )

    def test_audit_hash_chain_and_no_semantic_content(self):
        gate = AuroraCapabilityReference()
        gate.evaluate(self.req("C0", "reason"), self.evidence())
        gate.evaluate(self.req("C1", "restricted_read"), self.evidence())
        events = gate.audit_events()
        self.assertEqual(len(events), 2)
        self.assertEqual(events[1]["previous_hash"], events[0]["hash"])
        self.assertNotIn("evidence", events[0])


if __name__ == "__main__":
    unittest.main()
