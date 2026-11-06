"""Offline validation for the proposed Kyro marketing site.

This test does not claim the site is deployed or user onboarding is complete.
"""
from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"cloud"/"kyro-launch"
PACK_ROOT=ROOT/"examples"/"modules"


class Inspect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs=[]
        self.inline_script=False
        self.a=[]
        self.ids=set()

    def handle_starttag(self, tag, attrs):
        d=dict(attrs)
        if "id" in d:
            assert d["id"] not in self.ids, f"duplicate element ID {d['id']}"
            self.ids.add(d["id"])
        if tag=="script":
            if "src" not in d:self.inline_script=True
            else:self.refs.append(d["src"])
        if tag=="link" and d.get("rel")=="stylesheet":self.refs.append(d.get("href",""))
        if tag=="a":self.a.append(d.get("href",""))


def run():
    for path in ["index.html","styles.css","app.js","catalog.json","README.md"]:
        assert (SITE/path).is_file(),path
    html=(SITE/"index.html").read_text(encoding="utf-8")
    js=(SITE/"app.js").read_text(encoding="utf-8")
    css=(SITE/"styles.css").read_text(encoding="utf-8")
    c=json.loads((SITE/"catalog.json").read_text(encoding="utf-8"))
    check=Inspect()
    check.feed(html)
    assert not check.inline_script
    assert check.ids.issuperset({"modules","collaboration","how-it-works","module-grid","catalog-status"})
    for ref in check.refs:
        uri=urlsplit(ref)
        assert not uri.scheme and not uri.netloc and ".." not in Path(uri.path).parts
        assert (SITE/uri.path).is_file(),ref
    assert all(h.startswith("https://") or h.startswith("#") for h in check.a)
    assert "Build together." in html and "Grow with knowledge." in html
    assert "Private-alpha collaboration workspace" in html
    assert "not yet available" in html
    assert "Simultaneous live co-editing is not claimed" in html
    assert "not a live session" in html
    assert "No purchase required" in html
    assert "textContent" in js and "replaceChildren" in js
    assert "innerHTML" not in js and "localStorage" not in js
    assert "@media(max-width:720px)" in css and "prefers-reduced-motion" in css
    assert c["status"]=="public_preview_catalogue" and c["schema_version"]==1
    ids=set()
    for module in c["modules"]:
        assert module["id"] not in ids
        ids.add(module["id"])
        assert module["price"]=="Free"
        assert module["category"] in {"language","knowledge"}
        expected=f"https://github.com/Hakaiki808-NZ/aurora-genesis/blob/main/examples/modules/{module['id']}.json"
        assert module["href"]==expected
        pack=json.loads((PACK_ROOT/(module["id"]+".json")).read_text(encoding="utf-8"))
        assert pack["distribution"]=="open"
        assert pack["id"]==module["id"]
        assert module["chapters"]==len(pack["chapters"])
        if module["category"]=="language":
            assert pack.get("category")=="language"
    assert ids=={"spanish-basics","te-reo-maori-basics","physics-foundations"}
    print("KYRO_MARKETING=PASS")


if __name__=="__main__":
    run()
