"""Real bounded SQLite C2 mutations; all host/privileged operations remain denied."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from tools.aurora_c2_workspace_reference import C2Denied, C2Sandbox, TestEngineSigner


class C2WorkspaceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.signer = TestEngineSigner()
        self.worker = C2Sandbox(self.root / "data.sqlite3", self.signer.verification_key)
        self.common = dict(subject="operator-1", session="session-alpha", epoch=7,
                           scope="sandbox:notes", key="item_a")

    def grant(self, action="write", payload="hello", **kw):
        fields = {**self.common, **kw}
        target_request = fields.pop("target_request", "")
        return self.signer.issue(
            **fields, action=action, payload=payload, target_request=target_request
        )

    def test_reversible_write_commits_and_restores_original(self):
        original = self.grant(payload="hello")
        receipt = self.worker.execute(original, "hello")
        self.assertEqual(receipt["status"], "COMMITTED")
        self.assertEqual(receipt["execution_tier"], "C2")
        self.assertFalse(receipt["production_engine_qualified"])
        self.assertEqual(self.worker.inspect_test_resource("sandbox:notes", "item_a"), ("hello", 1))
        target = receipt["request_id"]
        rollback = self.grant(action="rollback", payload=target, target_request=target)
        receipt2 = self.worker.execute(rollback, target)
        self.assertEqual(receipt2["status"], "COMMITTED")
        self.assertIsNone(self.worker.inspect_test_resource("sandbox:notes", "item_a"))

    def test_restore_previous_value(self):
        first = self.grant(payload="first")
        self.worker.execute(first, "first")
        second = self.grant(payload="second")
        self.worker.execute(second, "second")
        rollback = self.grant(action="rollback", payload=second["request_id"],
                              target_request=second["request_id"])
        self.worker.execute(rollback, second["request_id"])
        self.assertEqual(self.worker.inspect_test_resource("sandbox:notes", "item_a"), ("first", 3))

    def test_rollback_conflict_fails_closed(self):
        first = self.grant(payload="first")
        self.worker.execute(first, "first")
        second = self.grant(payload="second")
        self.worker.execute(second, "second")
        rollback = self.grant(action="rollback", payload=first["request_id"], target_request=first["request_id"])
        with self.assertRaisesRegex(C2Denied, "conflict"):
            self.worker.execute(rollback, first["request_id"])
        self.assertEqual(self.worker.inspect_test_resource("sandbox:notes", "item_a"), ("second", 2))

    def test_signed_value_mutation_is_rejected(self):
        grant = self.grant(payload="hello")
        with self.assertRaisesRegex(C2Denied, "signed payload"):
            self.worker.execute(grant, "changed")
        with self.assertRaisesRegex(C2Denied, "signature"):
            self.worker.execute({**grant, "scope": "sandbox:other"}, "hello")

    def test_replay_is_denied(self):
        grant = self.grant()
        self.worker.execute(grant, "hello")
        with self.assertRaisesRegex(C2Denied, "replay"):
            self.worker.execute(grant, "hello")

    def test_only_sandbox_scope_and_approved_key(self):
        for scope, key in [
            ("prod:database", "item_a"), ("sandbox:../prod", "item_a"),
            ("sandbox:notes", "../../etc/passwd"), ("sandbox:notes", "foo/bar"),
            ("sandbox:notes", ".env"),
        ]:
            with self.subTest(scope=scope, key=key), self.assertRaises(C2Denied):
                self.grant(scope=scope, key=key)

    def test_only_reversible_actions(self):
        for action in ("shell", "sudo", "external", "privileged", "delete_database", "C5"):
            with self.subTest(action=action), self.assertRaises(C2Denied):
                self.grant(action=action)

    def test_binding_and_expiry(self):
        grant = self.grant(lifetime_seconds=1)
        with self.assertRaisesRegex(C2Denied, "signature"):
            self.worker.execute({**grant, "epoch": 8}, "hello")
        with self.assertRaisesRegex(C2Denied, "signature"):
            self.worker.execute({**grant, "session": "other"}, "hello")
        with self.assertRaisesRegex(C2Denied, "signature"):
            self.worker.execute({**grant, "expires_at": "2000-01-01T00:00:00Z"}, "hello")
        with self.assertRaisesRegex(C2Denied, "five minutes"):
            self.grant(lifetime_seconds=301)

    def test_rollback_only_same_session_and_key(self):
        grant = self.grant()
        self.worker.execute(grant, "hello")
        attempt = self.grant(action="rollback", payload=grant["request_id"],
                            target_request=grant["request_id"], session="different")
        with self.assertRaisesRegex(C2Denied, "binding mismatch"):
            self.worker.execute(attempt, grant["request_id"])

    def test_concurrent_replay_only_one_commits(self):
        grant = self.grant()
        def call(_):
            try:
                self.worker.execute(grant, "hello")
                return "ok"
            except C2Denied:
                return "denied"
        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(call, range(5)))
        self.assertEqual(results.count("ok"), 1)
        self.assertEqual(results.count("denied"), 4)

    def test_process_reopen_persists_receipts_and_data(self):
        grant = self.grant(payload="durable")
        self.worker.execute(grant, "durable")
        new_worker = C2Sandbox(self.root / "data.sqlite3", self.signer.verification_key)
        self.assertEqual(new_worker.inspect_test_resource("sandbox:notes", "item_a"), ("durable", 1))
        with self.assertRaisesRegex(C2Denied, "replay"):
            new_worker.execute(grant, "durable")

    def test_no_ambiguous_rollback_of_already_reverted(self):
        write = self.grant()
        self.worker.execute(write, "hello")
        original = write["request_id"]
        undo = self.grant(action="rollback", payload=original, target_request=original)
        self.worker.execute(undo, original)
        second_undo = self.grant(action="rollback", payload=original, target_request=original)
        with self.assertRaisesRegex(C2Denied, "already reverted"):
            self.worker.execute(second_undo, original)

    def test_per_scope_quota(self):
        for index in range(100):
            k = f"k{index}"
            value = f"v{index}"
            grant = self.grant(key=k, payload=value)
            self.worker.execute(grant, value)
        extra = self.grant(key="new_one", payload="extra")
        with self.assertRaisesRegex(C2Denied, "quota"):
            self.worker.execute(extra, "extra")

    def test_payload_bounded_and_no_symlink_database(self):
        with self.assertRaisesRegex(C2Denied, "payload"):
            self.grant(payload="x" * 4097)
        symlink = self.root / "db-link.sqlite"
        symlink.symlink_to(self.root / "data.sqlite3")
        with self.assertRaisesRegex(C2Denied, "symlink"):
            C2Sandbox(symlink, self.signer.verification_key)

    def test_untrusted_signer_cannot_authorize(self):
        impostor = TestEngineSigner()
        forgery = impostor.issue(**self.common, action="write", payload="hello")
        with self.assertRaisesRegex(C2Denied, "signature"):
            self.worker.execute(forgery, "hello")


if __name__ == "__main__":
    unittest.main()
