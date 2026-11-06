"""Fail-fast static contract checks for the cloud research beta.

These are not substitutes for a penetration test or cloud integration test.
"""
from __future__ import annotations
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run():
    handler = (ROOT/"cloud/aws/handler.py").read_text(encoding="utf-8")
    template = (ROOT/"cloud/aws/beta.yaml").read_text(encoding="utf-8")
    app = (ROOT/"cloud/web/app.js").read_text(encoding="utf-8")
    html = (ROOT/"cloud/web/index.html").read_text(encoding="utf-8")
    ast.parse(handler, filename="cloud/aws/handler.py")
    assert "STATE_BUCKET" in handler
    assert "IfMatch" in handler and "IfNoneMatch" in handler
    assert "MAX_MESSAGE = 2000" in handler and "MAX_STATE" in handler
    assert "enable_ollama=False" in handler
    assert '"aurora_attached": False' in handler
    assert template.count("AuthorizationType: JWT") == 2
    assert "AuthorizationScopes: [aws.cognito.signin.user.admin]" in template
    assert "AllowedOAuthFlows: [code]" in template
    assert "MfaConfiguration: 'OFF'" in template  # beta limitation remains explicit
    assert "AllowAdminCreateUserOnly: false" in template  # beta signup, not public launch
    assert "BlockPublicAcls: true" in template
    assert "BlockPublicPolicy: true" in template
    assert "ResponseHeadersPolicy" in template
    assert "ThrottlingRateLimit: 1" in template
    assert "ExpirationInDays: 7" in template
    assert "version" in template and "GetObjectVersion" in template
    assert "code_challenge_method" in app and "S256" in app
    assert "sessionStorage" in app and "textContent" in app
    assert "innerHTML" not in app and "eval(" not in app
    assert "No Aurora execution" in html
    print("CLOUD_BETA_STATIC=PASS")

if __name__ == "__main__":
    run()
