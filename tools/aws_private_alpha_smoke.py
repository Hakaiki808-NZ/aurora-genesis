#!/usr/bin/env python3
"""Read-only AWS private-alpha smoke checks for the public Kyro entrypoints.

No AWS credentials, test accounts, model inference, or privileged engine access.
The two protected routes must reject anonymous requests at API Gateway.
"""
from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SITE = os.getenv("KYRO_SITE_URL", "https://d3j65cc3p66kzr.cloudfront.net").rstrip("/")
API = os.getenv("KYRO_API_URL", "https://ces52hcf3e.execute-api.ap-southeast-2.amazonaws.com").rstrip("/")
TIMEOUT = 12


def request(url: str, method: str = "GET", body: bytes | None = None) -> tuple[int, bytes]:
    headers = {"User-Agent": "Aurora-Genesis-private-alpha-smoke/1.0"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = Request(url, method=method, headers=headers, data=body)
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.read(64 * 1024)
    except HTTPError as error:
        return error.code, error.read(64 * 1024)


def main() -> int:
    failures: list[str] = []

    for label, url in [("Kyro entry", SITE + "/"), ("Kyro workspace", SITE + "/v3/index.html")]:
        try:
            status, content = request(url)
            if status != 200 or not content:
                failures.append(f"{label}: expected non-empty HTTP 200, got {status}")
            else:
                print(f"PASS {label}: HTTP 200")
        except (URLError, TimeoutError, OSError) as exc:
            failures.append(f"{label}: network error ({type(exc).__name__})")

    try:
        status, raw = request(API + "/api/v3/health")
        if status != 200:
            failures.append(f"Kyro health: expected HTTP 200, got {status}")
        else:
            value = json.loads(raw)
            if value.get("service") != "kyro-cloud-core":
                failures.append("Kyro health: unexpected service identifier")
            if value.get("aurora_execution") != "disabled":
                failures.append("Kyro health: Aurora execution status changed; security review required")
            if value.get("inference") not in ("genesis-research-reference", "not-connected"):
                failures.append("Kyro health: unexpected inference status")
            print("PASS Kyro public health (no inference invocation)")
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        failures.append(f"Kyro health: request/JSON error ({type(exc).__name__})")

    cases = [
        ("private readiness", "GET", "/api/v3/readiness", None),
        ("private projects", "GET", "/api/v3/projects", None),
        ("private conversation mutation", "POST", "/api/v3/conversations", b'{"title":"unauthorized-probe"}'),
    ]
    for label, method, path, body in cases:
        try:
            status, _ = request(API + path, method, body)
            if status not in (401, 403):
                failures.append(f"{label}: anonymous access returned HTTP {status}, expected 401/403")
            else:
                print(f"PASS {label}: anonymous HTTP {status}")
        except (URLError, TimeoutError, OSError) as exc:
            failures.append(f"{label}: network error ({type(exc).__name__})")

    for failure in failures:
        print("FAIL " + failure, file=sys.stderr)
    if failures:
        print(f"{len(failures)} private-alpha smoke check(s) failed", file=sys.stderr)
        return 1
    print("All public-edge checks passed. This does NOT certify Aurora or full JWT login.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
