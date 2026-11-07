"""Offline tests for JWT-gated, research-only Genesis Lambda routes."""
from __future__ import annotations

import importlib.util
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch


def run():
    root=Path(__file__).resolve().parents[1]
    file=root/"cloud/genesis-lora-inference/handler.py"
    spec=importlib.util.spec_from_file_location("test_genesis_lambda_handler",file)
    module=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    issuer="https://cognito-idp.ap-southeast-2.amazonaws.com/test-pool"
    audience="test-client"
    claims={"iss":issuer,"aud":audience,"sub":"unit-test-only",
            "exp":4102444800,"token_use":"id"}
    def event(method,path,body=None,identity=True):
        return {"version":"2.0","rawPath":path,
                "requestContext":{
                    "http":{"method":method,"path":path},
                    "authorizer":{"jwt":{"claims":claims if identity else {}}}},
                "isBase64Encoded":False,
                "body":json.dumps(body) if body is not None else None}

    with patch.dict(os.environ,{"KYRO_JWT_ISSUER":issuer,
                               "KYRO_JWT_AUDIENCE":audience}):
        assert module.lambda_handler(event("GET","/api/v3/neural/status",identity=False),None)["statusCode"]==401
        healthy=module.lambda_handler(event("GET","/api/v3/neural/status"),None)
        assert healthy["statusCode"]==200
        data=json.loads(healthy["body"])
        assert data["test_status"]=="research_only_not_production_qualified"
        assert data["aurora_execution"]=="disabled"
        assert data["limits"]["monthly_total_requests"]==80
        assert module.lambda_handler(event("POST","/api/v3/neural/chat",{"message":""}),None)["statusCode"]==400
        assert module.lambda_handler(event("POST","/api/v3/neural/chat",{"message":"x"*2600}),None)["statusCode"]==400
        assert module.lambda_handler(event("POST","/api/v3/neural/chat",{"message":"test"},False),None)["statusCode"]==401
        assert module.lambda_handler(event("GET","/api/v3/neural/not-there"),None)["statusCode"]==404
        bad=event("POST","/api/v3/neural/chat")
        bad["body"]="{invalid"
        assert module.lambda_handler(bad,None)["statusCode"]==400
    print("GENESIS_NEURAL_SERVICE=PASS")


if __name__=="__main__":
    run()
