"""Check that the version-controlled Kyro beta web snapshot is self-contained.

This test is read-only, works offline, and does not treat static assets as proof
of a working sign-in, model inference, or Aurora execution.
"""
from __future__ import annotations
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1] / "cloud" / "public-beta-web"


class LocalAssets(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.refs: list[str] = []
        self.inline_script = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "script":
            if not values.get("src"):
                self.inline_script = True
            else:
                self.refs.append(values["src"])
        if tag == "link" and values.get("rel") == "stylesheet" and values.get("href"):
            self.refs.append(values["href"])


def test_snapshot() -> None:
    manifest = json.loads((ROOT / "asset-manifest.json").read_text(encoding="utf-8"))
    assert manifest["snapshot_date_nz"] == "2026-11-10"
    assert len(manifest["assets"]) >= 16
    seen: set[str] = set()
    for entry in manifest["assets"]:
        key = entry["path"]
        assert key not in seen and not key.startswith("/") and ".." not in Path(key).parts
        seen.add(key)
        path = ROOT / key
        assert path.is_file(), f"Missing deployed web file: {key}"
        assert len(path.read_bytes()) == entry["bytes"], f"Changed snapshot without manifest update: {key}"
        assert entry["etag"], f"Missing origin ETag for {key}"

    htmls = ["index.html", "v3/index.html", "v3/preview.html", "v3/realignment-preview.html"]
    for name in htmls:
        raw = (ROOT / name).read_text(encoding="utf-8")
        parser = LocalAssets()
        parser.feed(raw)
        assert not parser.inline_script, f"CSP-incompatible inline script: {name}"
        assert not re.search(r"""(?:href|src)\s*=\s*["']javascript:""", raw, re.I)
        for ref in parser.refs:
            url = urlsplit(ref)
            if url.scheme or url.netloc or ref.startswith("//"):
                continue
            if url.path.startswith("/"):
                rel = url.path.lstrip("/")
            else:
                rel = str(Path(name).parent / url.path)
            assert (ROOT / rel).is_file(), f"Broken public asset {ref} in {name}"

    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    assert config["apiUrl"].startswith("https://")
    assert config["cognitoDomain"].startswith("https://")
    assert config["redirectUri"].startswith("https://d3j65cc3p66kzr.cloudfront.net/")
    root = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "No Aurora execution" in root
    app = (ROOT / "app.js").read_text(encoding="utf-8")
    assert "code_challenge_method" in app and "S256" in app
    assert "textContent" in app

    workspace = (ROOT / "v3/index.html").read_text(encoding="utf-8")
    neural = (ROOT / "v3/neural.js").read_text(encoding="utf-8")
    assert '<script defer src="/v3/neural.js"></script>' in workspace
    assert all('id="' + name + '"' in workspace for name in (
        "neural-form", "neural-input", "neural-status", "neural-answer", "neural-detail"
    ))
    assert "window.api('/neural/chat', 'POST', { message })" in neural
    assert "window.api('/neural/status')" in neural
    assert "answer.textContent = data.answer" in neural
    assert ".innerHTML" not in neural, "Neural output must be plain text"
    assert "d397hqqvk3qah2.cloudfront.net/v3/index.html" in (
        ROOT / "v3/app.js"
    ).read_text(encoding="utf-8")
    print(f"PASS: {len(seen)} recorded web assets, local references, PKCE, neural-only scope and beta disclosures")


if __name__ == "__main__":
    test_snapshot()
