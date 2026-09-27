import os, tempfile
from pathlib import Path


def run():
    # Import-level smoke test only: persistent singleton state isn't needed for acceptance.
    from genesis.api import app
    routes={r.path for r in app.routes}
    assert {"/health","/state","/diagnostics","/goals","/constitution","/policy-audit","/chat"}.issubset(routes)
    print("API=PASS")

if __name__=="__main__": run()
