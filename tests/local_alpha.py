"""Real HTTP smoke test for the local Kyro/Genesis trust boundary."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "test-kyro-access-token-not-for-public-use"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def request(url: str, *, token: str | None = None, payload: dict | None = None):
    headers = {}
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if payload is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            body = response.read().decode("utf-8")
            return response.status, response.headers, json.loads(body) if url.endswith(("/api/chat", "/api/status")) else body
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read().decode("utf-8")


def start_server(env, port):
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "kyro.app:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base = "http://127.0.0.1:" + str(port)
    try:
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise AssertionError("Kyro server exited before becoming ready")
            try:
                result = request(base + "/")
                if result[0] == 200:
                    return proc, base
            except (OSError, TimeoutError):
                time.sleep(0.15)
        raise AssertionError("Kyro server did not become ready")
    except Exception:
        proc.terminate()
        proc.wait(timeout=5)
        raise


def stop_server(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def run():
    with tempfile.TemporaryDirectory() as td:
        env = os.environ.copy()
        env.update({
            "KYRO_ACCESS_TOKEN": TOKEN,
            "GENESIS_STATE_PATH": str(Path(td) / "state.db"),
            "GENESIS_WORKSPACE": str(Path(td) / "workspace"),
            "GENESIS_GENERATOR": "none",
            "GENESIS_CAPABILITY_LEVEL": "C3",
        })
        port = free_port()
        proc, base = start_server(env, port)
        try:
            code, headers, html = request(base + "/")
            assert code == 200 and "Kyro" in html
            assert headers["X-Frame-Options"] == "DENY"
            assert "default-src 'none'" in headers["Content-Security-Policy"]
            assert request(base + "/api/status")[0] == 401
            assert request(base + "/api/status", token="invalid-token")[0] == 401
            assert request(base + "/api/chat", payload={"message": "test"})[0] == 401
            code, _, data = request(base + "/api/status", token=TOKEN)
            assert code == 200 and data["model_health"]["ok"], data
            assert data["aurora_attached"] is False
            assert data["public_deployment_qualified"] is False
            code, _, data = request(base + "/api/chat", token=TOKEN, payload={"message": "Learn that launch marker is COBALT."})
            assert code == 200, data
            code, _, data = request(base + "/api/chat", token=TOKEN, payload={"message": "What is launch marker?"})
            assert code == 200 and "COBALT" in data["answer"], data
            assert request(base + "/api/chat", token=TOKEN, payload={"message": ""})[0] == 422
            assert request(base + "/api/chat", token=TOKEN, payload={"message": "x" * 16001})[0] == 422
        finally:
            stop_server(proc)

        proc2, base = start_server(env, port)
        try:
            code, _, data = request(base + "/api/chat", token=TOKEN, payload={"message": "What is launch marker?"})
            assert code == 200 and "COBALT" in data["answer"], data
        finally:
            stop_server(proc2)
    print("LOCAL_ALPHA_HTTP=PASS")


if __name__ == "__main__":
    run()
