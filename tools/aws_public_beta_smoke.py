#!/usr/bin/env python3
"""Read-only live Kyro web smoke. Never sends credentials or private user data."""
from __future__ import annotations

import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# The recovery website replaced the retired beta domain. Override for staging.
SITE = os.getenv("KYRO_SITE_URL", "https://d397hqqvk3qah2.cloudfront.net").rstrip("/")
RESEARCH_API = os.getenv(
    "KYRO_RESEARCH_API",
    "https://mex7yuj2j2.execute-api.ap-southeast-2.amazonaws.com",
).rstrip("/")

ASSETS = (
    "/", "/site.css", "/site.js",
    "/v3/index.html", "/v3/app.js", "/v3/preview.html",
    "/v3/realignment-preview.html", "/v3/school-voice.js",
)


def fetch(url: str, method: str = "GET", data: bytes | None = None):
    req = Request(url, method=method, data=data, headers={
        "User-Agent": "Kyro-public-beta-gate/1.1",
        **({"Content-Type": "application/json"} if data is not None else {}),
    })
    try:
        with urlopen(req, timeout=12) as response:
            return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read(32768)
    except HTTPError as err:
        return err.code, {k.lower(): v for k, v in err.headers.items()}, err.read(4096)


def main() -> int:
    failed: list[str] = []
    if not SITE.startswith("https://") or not RESEARCH_API.startswith("https://"):
        print("FAIL: smoke targets must use HTTPS", file=sys.stderr)
        return 1

    for path in ASSETS:
        try:
            status, headers, content = fetch(SITE + path)
            if status != 200 or not content:
                failed.append(f"{path}: expected nonempty 200, got {status}")
            if path == "/":
                for header in ("strict-transport-security", "content-security-policy", "x-content-type-options"):
                    if not headers.get(header):
                        failed.append(f"Missing CloudFront security header: {header}")
            if path == "/site.js" and b"/v3/index.html" not in content:
                failed.append("Public site has no reachable workspace link")
            if path == "/v3/app.js" and (SITE + "/v3/index.html").encode() not in content:
                failed.append("Workspace OAuth redirect does not match the deployed site")
            print(f"Static {path}: {status}")
        except (URLError, OSError, TimeoutError) as exc:
            failed.append(f"{path}: unreachable ({type(exc).__name__}: {str(exc)[:160]})")

    # These endpoints must remain inaccessible without an identity token.
    for method, path, data in (
        ("GET", "/api/status", None),
        ("POST", "/api/chat", b'{"message":"anonymous-test"}'),
    ):
        try:
            status, _, _ = fetch(RESEARCH_API + path, method, data)
            if status not in (401, 403):
                failed.append(f"Anonymous research API {method} {path}: expected denial, got {status}")
            print(f"Anonymous research {method} {path}: {status}")
        except (URLError, OSError, TimeoutError) as exc:
            failed.append(f"Anonymous research {path}: unreachable ({type(exc).__name__})")

    for msg in failed:
        print("FAIL: " + msg, file=sys.stderr)
    if failed:
        return 1
    print("PASS: public assets, browser redirect and anonymous access barriers.")
    print("NOTE: invited-user login, project isolation and neural quality require separate tests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
