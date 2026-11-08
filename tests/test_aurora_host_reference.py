"""Negative security and command-construction tests for Aurora C1 host reference."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.aurora_host_c1_reference import (
    AdmissionDenied, Limits, build_command, execute_c1, host_preflight,
)


class AuroraHostReferenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.bin = Path(self.tmp.name) / "reference-worker"
        self.bin.write_bytes(b"#!/bin/sh\nexit 0\n")
        self.bin.chmod(0o700)
        self.sha = hashlib.sha256(self.bin.read_bytes()).hexdigest()
        self.limits = Limits(cpu_percent=20, memory_bytes=64 * 1024 * 1024,
                             tasks=4, runtime_seconds=5, io_weight=100)

    def build(self, **kw):
        opts = {"capability": "C1", "binary_sha256": self.sha}
        opts.update(kw)
        with patch("tools.aurora_host_c1_reference.host_preflight",
                   return_value={"qualified": True}):
            return build_command([str(self.bin), "hello"], self.limits, **opts)

    def test_no_implicit_execution(self):
        with patch("tools.aurora_host_c1_reference.subprocess.run") as run:
            command = self.build()
            run.assert_not_called()
        self.assertIn("--property=PrivateNetwork=yes", command)
        self.assertIn("--property=NoNewPrivileges=yes", command)
        self.assertIn("--property=MemoryMax=67108864", command)
        self.assertIn("--property=CPUQuota=20%", command)
        self.assertIn("--property=TasksMax=4", command)
        self.assertIn("--property=RuntimeMaxSec=5s", command)
        self.assertIn("--property=IOWeight=100", command)
        self.assertEqual(command[0], "systemd-run")
        self.assertEqual(command[-3:], ["--", str(self.bin), "hello"])
        self.assertNotIn("/bin/sh", command[:-3])

    def test_high_consequence_tiers_always_denied(self):
        for level in ("C2", "C3", "C4", "C5", "SUPREME", ""):
            with self.subTest(level=level), self.assertRaises(AdmissionDenied):
                self.build(capability=level)

    def test_mutated_executable_denied(self):
        self.bin.write_bytes(b"#!/bin/sh\nexit 1\n")
        with self.assertRaisesRegex(AdmissionDenied, "hash mismatch"):
            self.build()

    def test_bad_account_denied(self):
        for account in ("root", "not valid", "../worker"):
            with self.subTest(account=account), self.assertRaises(AdmissionDenied):
                self.build(service_user=account)

    def test_limits_fail_closed(self):
        candidates = (
            Limits(0, 64 * 1024 * 1024, 4, 5),
            Limits(20, 4096, 4, 5),
            Limits(20, 64 * 1024 * 1024, 99, 5),
            Limits(20, 64 * 1024 * 1024, 4, 0),
            Limits(20, 64 * 1024 * 1024, 4, 5, 10001),
        )
        for candidate in candidates:
            with self.subTest(candidate=candidate):
                with self.assertRaises(AdmissionDenied):
                    candidate.validate()

    def test_missing_kernel_enforcement_denied(self):
        with patch("tools.aurora_host_c1_reference.host_preflight",
                   return_value={"qualified": False}):
            with self.assertRaisesRegex(AdmissionDenied, "cgroup"):
                build_command([str(self.bin)], self.limits, capability="C1",
                              binary_sha256=self.sha)

    def test_nonabsolute_command_denied(self):
        with self.assertRaises(AdmissionDenied):
            build_command(["relative-worker"], self.limits, capability="C1", binary_sha256=self.sha)

    def test_success_receipt_identifies_transient_unit(self):
        with patch("tools.aurora_host_c1_reference.host_preflight",
                   return_value={"qualified": True}), patch(
                       "tools.aurora_host_c1_reference.subprocess.run",
                       return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
            receipt = execute_c1([str(self.bin)], self.limits, binary_sha256=self.sha)
        self.assertEqual(receipt["status"], "EXITED")
        self.assertTrue(receipt["unit"].startswith("aurora-c1-"))
        self.assertEqual(run.call_args.kwargs["check"], False)
        self.assertEqual(run.call_args.kwargs["timeout"], 20)

    def test_no_success_receipt_on_failure(self):
        with patch("tools.aurora_host_c1_reference.host_preflight",
                   return_value={"qualified": True}), patch(
                       "tools.aurora_host_c1_reference.subprocess.run",
                       return_value=subprocess.CompletedProcess([], 2, "", "")):
            with self.assertRaisesRegex(AdmissionDenied, "no successful receipt"):
                execute_c1([str(self.bin)], self.limits, binary_sha256=self.sha)

    def test_no_success_receipt_on_timeout(self):
        with patch("tools.aurora_host_c1_reference.host_preflight",
                   return_value={"qualified": True}), patch(
                       "tools.aurora_host_c1_reference.subprocess.run",
                       side_effect=subprocess.TimeoutExpired([], 1)):
            with self.assertRaisesRegex(AdmissionDenied, "timed out"):
                execute_c1([str(self.bin)], self.limits, binary_sha256=self.sha)


if __name__ == "__main__":
    unittest.main()
