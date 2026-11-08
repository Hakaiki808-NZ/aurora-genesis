#!/usr/bin/env python3
"""Linux host-target reference adapter for bounded Aurora C1 tasks.

This is a publicly reviewable qualification helper, NOT the protected Aurora
runtime or an authority to promote privileged operations. It refuses C2–C5.
Use only on a provisioned, isolated Linux host with a dedicated service account.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid


class AdmissionDenied(RuntimeError):
    """Execution cannot be safely admitted on this host."""


@dataclass(frozen=True)
class Limits:
    cpu_percent: int
    memory_bytes: int
    tasks: int
    runtime_seconds: int
    io_weight: int = 100

    def validate(self) -> None:
        if not 1 <= self.cpu_percent <= 100:
            raise AdmissionDenied("CPU quota out of C1 range")
        if not 16 * 1024 * 1024 <= self.memory_bytes <= 512 * 1024 * 1024:
            raise AdmissionDenied("memory limit out of C1 range")
        if not 1 <= self.tasks <= 32:
            raise AdmissionDenied("task count out of C1 range")
        if not 1 <= self.runtime_seconds <= 60:
            raise AdmissionDenied("runtime deadline out of C1 range")
        if not 1 <= self.io_weight <= 10000:
            raise AdmissionDenied("I/O weight out of range")


def host_preflight() -> dict[str, object]:
    root = Path("/sys/fs/cgroup")
    controllers_file = root / "cgroup.controllers"
    controllers = set(controllers_file.read_text().split()) if controllers_file.is_file() else set()
    required = {"cpu", "memory", "pids", "io"}
    systemd_available = bool(shutil.which("systemd-run")) and Path("/run/systemd/system").exists()
    return {
        "linux": sys.platform == "linux",
        "cgroup_v2": controllers_file.is_file(),
        "controllers": sorted(controllers),
        "required_controllers": sorted(required),
        "systemd": systemd_available,
        "qualified": sys.platform == "linux" and required <= controllers and systemd_available,
    }


def build_command(
    argv: list[str],
    limits: Limits,
    *,
    capability: str,
    binary_sha256: str,
    service_user: str = "aurora-worker",
    unit_id: str | None = None,
) -> list[str]:
    """Construct a single transient systemd service. Never uses a shell."""
    if capability != "C1":
        raise AdmissionDenied("C2-C5 and privileged Engine actions remain disabled")
    limits.validate()
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,30}", service_user) or service_user == "root":
        raise AdmissionDenied("a dedicated unprivileged service user is mandatory")
    if not argv or any(not isinstance(x, str) or not x or "\x00" in x for x in argv):
        raise AdmissionDenied("command arguments invalid")
    binary = Path(argv[0])
    if not binary.is_absolute() or not binary.is_file():
        raise AdmissionDenied("executable must be an existing absolute file")
    if not re.fullmatch(r"[a-f0-9]{64}", binary_sha256):
        raise AdmissionDenied("a pinned executable SHA256 is mandatory")
    digest = hashlib.sha256()
    with binary.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != binary_sha256:
        raise AdmissionDenied("executable hash mismatch")
    if not host_preflight()["qualified"]:
        raise AdmissionDenied("host has no verified cgroup v2/systemd enforcement")
    unit = unit_id or "aurora-c1-" + uuid.uuid4().hex
    if not re.fullmatch(r"aurora-c1-[a-zA-Z0-9-]{1,64}", unit):
        raise AdmissionDenied("invalid unit identifier")
    return [
        "systemd-run", "--system", "--wait", "--collect", "--pipe", "--quiet",
        "--service-type=exec", "--unit=" + unit,
        "--property=User=" + service_user,
        "--property=CPUQuota=" + str(limits.cpu_percent) + "%",
        "--property=MemoryMax=" + str(limits.memory_bytes),
        "--property=TasksMax=" + str(limits.tasks),
        "--property=RuntimeMaxSec=" + str(limits.runtime_seconds) + "s",
        "--property=IOWeight=" + str(limits.io_weight),
        "--property=NoNewPrivileges=yes",
        "--property=CapabilityBoundingSet=",
        "--property=PrivateTmp=yes",
        "--property=PrivateNetwork=yes",
        "--property=ProtectSystem=strict",
        "--property=ProtectHome=yes",
        "--property=ProtectKernelTunables=yes",
        "--property=ProtectControlGroups=yes",
        "--property=ProtectKernelModules=yes",
        "--property=RestrictSUIDSGID=yes",
        "--", *argv,
    ]


def execute_c1(
    argv: list[str], limits: Limits, *, binary_sha256: str,
    service_user: str = "aurora-worker",
) -> dict[str, object]:
    """Opt-in host execution; caller must independently authorize the task."""
    command = build_command(argv, limits, capability="C1",
                            binary_sha256=binary_sha256, service_user=service_user)
    try:
        result = subprocess.run(
            command, capture_output=True, text=True,
            timeout=limits.runtime_seconds + 15, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AdmissionDenied("systemd enforcement failed or timed out") from exc
    if result.returncode:
        raise AdmissionDenied("bounded C1 task failed; no successful receipt issued")
    return {"status": "EXITED", "returncode": 0, "unit": command[7].removeprefix("--unit=")}


def main() -> int:
    parser = argparse.ArgumentParser(description="Aurora Linux cgroup admission preflight")
    parser.add_argument("--check-host", action="store_true",
                        help="Read-only check; no operation is admitted by this flag")
    args = parser.parse_args()
    if not args.check_host:
        parser.error("only --check-host is exposed by this reference CLI")
    report = host_preflight()
    print(json.dumps(report, sort_keys=True))
    return 0 if report["qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
