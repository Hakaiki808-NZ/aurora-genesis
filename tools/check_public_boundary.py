#!/usr/bin/env python3
"""Fail-closed guard for accidentally publishing sensitive files or obvious credentials.

This checks the currently tracked Git tree, not Git history or GitHub settings.
A clean result is NOT a complete security audit.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys

DISALLOWED_DIRS = (
    ".aws/", ".ssh/", "secrets/", "private-engine/",
    "aurora/private/", "infra/secrets/", "deploy/private/",
)
DISALLOWED_BASENAMES = {
    "credentials", "service-account.json", "service_account.json",
    "id_rsa", "id_ed25519", ".npmrc", ".pypirc",
}
DISALLOWED_SUFFIXES = (
    ".pem", ".key", ".p8", ".p12", ".pfx", ".jks", ".kdbx",
    ".tfstate", ".tfstate.backup", ".sqlite", ".sqlite3", ".db",
)
PATTERNS = {
    "AWS access key identifier": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "GitHub access token": re.compile(r"\b(?:ghp_|gho_|ghu_|ghs_|ghr_|github_pat_)[A-Za-z0-9_]{20,}\b"),
    "OpenAI or Bedrock bearer credential": re.compile(r"\b(?:sk-(?:proj-|svcacct-)?|bedrock-api-key-)[A-Za-z0-9_-]{24,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "Slack access token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "private key PEM": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"),
    "URL-embedded credentials": re.compile(r"https?://[^\s/@:]+:[^\s/@]+@"),
}
MAX_FILE_BYTES = 2_000_000


def forbidden_path(name: str) -> bool:
    normalized = name.replace("\\", "/")
    parts = normalized.split("/")
    basename = parts[-1].lower()
    if any(normalized.lower().startswith(prefix) for prefix in DISALLOWED_DIRS):
        return True
    if basename in DISALLOWED_BASENAMES:
        return True
    if basename == ".env" or (basename.startswith(".env.") and basename != ".env.example"):
        return True
    if basename.endswith(DISALLOWED_SUFFIXES):
        return True
    return False


def scan_text(text: str) -> list[str]:
    return [name for name, pattern in PATTERNS.items() if pattern.search(text)]


def check_repository(root: Path) -> list[str]:
    try:
        result = subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
    except (OSError, subprocess.CalledProcessError) as exc:
        return [f"unable to list tracked Git files ({type(exc).__name__})"]
    findings: list[str] = []
    for raw in result.split(b"\x00"):
        if not raw:
            continue
        name = raw.decode("utf-8", "replace")
        if forbidden_path(name):
            findings.append(f"{name}: path reserved for private data")
            continue
        file = root / name
        if not file.is_file():
            continue
        size = file.stat().st_size
        if size > MAX_FILE_BYTES:
            findings.append(f"{name}: file too large for bounded scan; review separately")
            continue
        data = file.read_bytes()
        if b"\x00" in data:
            findings.append(f"{name}: binary file requires explicit review")
            continue
        for category in scan_text(data.decode("utf-8", "replace")):
            findings.append(f"{name}: {category} detected (value suppressed)")
    return findings


def self_test() -> None:
    assert forbidden_path(".env")
    assert forbidden_path("deploy/oss/.env.production")
    assert not forbidden_path("deploy/oss/.env.example")
    assert forbidden_path("private-engine/angel.py")
    assert forbidden_path("secrets/prod.json")
    assert not forbidden_path("genesis/engine_boundary.py")
    assert scan_text("AKIA" + "Q" * 16) == ["AWS access key identifier"]
    assert scan_text("-----BEGIN " + "PRIVATE KEY-----") == ["private key PEM"]
    assert scan_text("https://user:password@host.invalid")
    assert not scan_text("os.getenv('AWS_ACCESS_KEY_ID') and a fake example")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print("Public-boundary scanner self-tests passed")
    else:
        root = Path(__file__).resolve().parents[1]
        findings = check_repository(root)
        for finding in findings:
            print("BLOCK: " + finding, file=sys.stderr)
        if findings:
            print(f"Public-boundary scan failed: {len(findings)} finding(s).", file=sys.stderr)
            sys.exit(1)
        print("Tracked-file public-boundary scan passed (history and external deployments NOT assessed).")
