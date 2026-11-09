"""Temporary Kyro feature-freeze gate for pull-request changes.

This is a source-scope check, not deployment enforcement or a security review.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

FROZEN_PATHS = (
    "web/kyro/",
    "cloud/public-site-v1/",
    "cloud/public-beta-web/",
    "cloud/kyro-launch/",
)
MAINTENANCE_TITLE = re.compile(r"^(?:fix|hotfix|security|test|refactor|chore)(?:\([^)]{1,80}\))?:", re.I)
EXCEPTION_MARKER = "Kyro-freeze-exception: stabilization"


def changed_ui_files(paths: list[str]) -> list[str]:
    return [p for p in paths if any(p.startswith(prefix) for prefix in FROZEN_PATHS)]


def freeze_violation(paths: list[str], title: str, body: str) -> str | None:
    changed = changed_ui_files(paths)
    if not changed:
        return None
    if MAINTENANCE_TITLE.match(title.strip()) and EXCEPTION_MARKER in body.splitlines():
        return None
    return (
        "Kyro feature freeze: changes to frozen UI paths need a maintenance-class "
        "PR title (fix:, hotfix:, security:, test:, refactor:, chore:) AND a "
        "'Kyro-freeze-exception: stabilization' line in the PR body. "
        "Feature expansion is deferred. Paths: " + ", ".join(changed[:12])
    )


def main() -> int:
    base = os.environ.get("PR_BASE_SHA", "").strip()
    if not re.fullmatch(r"[0-9a-fA-F]{40}", base):
        print("Kyro freeze: missing or invalid PR_BASE_SHA", file=sys.stderr)
        return 2
    run = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", base, "HEAD"],
        check=True, text=True, capture_output=True,
    )
    paths = [s for s in run.stdout.splitlines() if s.strip()]
    violation = freeze_violation(paths, os.environ.get("PR_TITLE", ""), os.environ.get("PR_BODY", ""))
    if violation:
        print(violation, file=sys.stderr)
        return 1
    print("KYRO_FEATURE_FREEZE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
