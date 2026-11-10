#!/usr/bin/env python3
"""Read-only anonymous public-beta edge smoke; never sends credentials or user data."""
from __future__ import annotations
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SITE = os.getenv("KYRO_SITE_URL", "https://d397hqqvk3qah2.cloudfront.net").rstrip("/")
RESEARCH_API = os.getenv("KYRO_RESEARCH_API", "https://mex7yuj2j2.execute-api.ap-southeast-2.amazonaws.com").rstrip("/")


def fetch(url: str, method: str = "GET", data: bytes | None = None):
    req = Request(url, method=method, data=data, headers={
        "User-Agent": "Kyro-public-beta-gate/1.0",
        **({"Content-Type": "application/json"} if data is not None else {})
    })
    try:
        with urlopen(req, timeout=12) as res:
            return res.status, {k.lower(): v for k, v in res.headers.items()}, res.read(1024 * 32)
    except HTTPError as err:
        return err.code, {k.lower(): v for k, v in err.headers.items()}, err.read(1024 * 4)


def main() -> int:
    failed: list[str] = []
    assets = ("/", "/site.css", "/site.js", "/v3/index.html",
              "/v3/app.js", "/v3/preview.html",
              "/v3/realignment-preview.html", "/v3/school-voice.js")
    for name in assets:
        try:
            status, headers, content = fetch(SITE + name)
            if status != 200 or not content:
                failed.append(f"{name} expected nonempty 200, got {status}")
            if name == "/":
                for h in ("strict-transport-security", "content-security-policy", "x-content-type-options"):
                    if not headers.get(h):
                        failed.append("Missing CloudFront response security header: " + h)
            print(f"Static {name}: {status}")
        except (URLError, OSError, TimeoutError) as exc:
            failed.append(f"{name} failed: {type(exc).__name__}")
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
            failed.append(f"Anonymous research API {path}: {type(exc).__name__}")
    for msg in failed:
        print("FAIL: " + msg, file=sys.stderr)
    if failed:
        return 1
    print("PASS: public assets and anonymous barriers. Authenticated usability is NOT established.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
