"""Start the isolated Kyro research interface on loopback only."""
from __future__ import annotations

import os
import secrets

import uvicorn


def main():
    if not os.environ.get("KYRO_ACCESS_TOKEN"):
        os.environ["KYRO_ACCESS_TOKEN"] = secrets.token_urlsafe(32)
    if len(os.environ["KYRO_ACCESS_TOKEN"]) < 24:
        raise SystemExit("KYRO_ACCESS_TOKEN must contain at least 24 characters.")
    # Text-only backend is deterministic. Set GENESIS_GENERATOR=ollama to opt in.
    os.environ.setdefault("GENESIS_GENERATOR", "none")
    os.environ.setdefault("GENESIS_CAPABILITY_LEVEL", "C3")
    print("KYRO LOCAL ALPHA: http://127.0.0.1:8767")
    print("ACCESS TOKEN: " + os.environ["KYRO_ACCESS_TOKEN"])
    print("Local research only: Aurora execution is not attached.")
    uvicorn.run("kyro.app:app", host="127.0.0.1", port=8767, workers=1, access_log=False)


if __name__ == "__main__":
    main()
