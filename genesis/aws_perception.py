"""Read-only AWS Lambda state perception: opt-in, allowlisted, non-attested.

This adapter samples AWS control-plane reports. It cannot issue Lambda Invoke,
change configuration, read function code, or grant Aurora/Genesis capabilities.
Its caller must be trusted and IAM-authorized. It does not expose AWS env vars.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Callable

from .perception import PerceptionCore

_REGION = re.compile(r"^[a-z]{2}(?:-gov)?-[a-z]+-\d+$")
_NAME = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
_STATES = {"Pending", "Active", "Inactive", "Failed"}
_UPDATES = {"InProgress", "Successful", "Failed"}


class AwsLambdaStateAdapter:
    """Observe approved Lambda states with a read-only AWS SDK client.

    This is independently testable using a fake client; boto3 is imported only
    when the feature is explicitly used.
    """

    def __init__(self, perception: PerceptionCore, *,
                 allowed_functions: set[str] | frozenset[str],
                 region: str = "ap-southeast-2",
                 client: Any | None = None,
                 clock: Callable[[], datetime] | None = None):
        if not isinstance(region, str) or not _REGION.fullmatch(region):
            raise ValueError("invalid AWS region")
        if not isinstance(allowed_functions, (set, frozenset)) or not allowed_functions:
            raise ValueError("explicit non-empty Lambda allowlist required")
        if len(allowed_functions) > 32 or any(not isinstance(n, str) or not _NAME.fullmatch(n)
                                               for n in allowed_functions):
            raise ValueError("invalid Lambda allowlist")
        self.world = perception
        self.region = region
        self.allowed = frozenset(allowed_functions)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        if client is None:
            import boto3
            from botocore.config import Config
            client = boto3.client("lambda", region_name=region,
                                  config=Config(connect_timeout=3, read_timeout=5,
                                                retries={"max_attempts": 2, "mode": "standard"}))
        self.client = client

    def sample(self, function_name: str) -> dict[str, Any]:
        if function_name not in self.allowed:
            raise PermissionError("function is not in the authorized observation allowlist")
        # AWS SDK/IAM supplies credential-backed control-plane data.
        # The returned source is not cryptographically attested by Aurora.
        response = self.client.get_function_configuration(FunctionName=function_name)
        arn = response.get("FunctionArn", "")
        pattern = (r"^arn:aws[a-z-]*:lambda:" + re.escape(self.region) +
                   r":\d{12}:function:" + re.escape(function_name) + r"$")
        if not isinstance(arn, str) or re.fullmatch(pattern, arn) is None:
            raise ValueError("AWS response function ARN does not match allowlist and region")
        state = response.get("State")
        update = response.get("LastUpdateStatus")
        if state not in _STATES or (update is not None and update not in _UPDATES):
            raise ValueError("unsupported or missing AWS Lambda state")
        instant = self.clock()
        if not isinstance(instant, datetime) or instant.tzinfo is None:
            raise ValueError("a timezone-aware sampling clock is required")
        instant = instant.astimezone(timezone.utc)
        signature = hashlib.sha256(arn.encode("utf-8")).hexdigest()[:24]
        group_hash = hashlib.sha256(arn.rsplit(":function:", 1)[0].encode("utf-8")).hexdigest()[:16]
        source = "aws.lambda." + signature
        self.world.register_source(source, source_kind="connector",
                                   independence_group="aws.controlplane." + group_hash)
        # Only allowlisted AWS state enums are written. Never persist AWS
        # Environment.Variables, Role, Code, Policies, tags, or returned errors.
        from uuid import uuid4
        base = {"source_id": source, "entity": "aws_lambda:" + function_name,
                "observed_at": instant, "ttl_seconds": 45}
        self.world.observe(event_id=str(uuid4()), attribute="state", value=state, **base)
        if update is not None:
            self.world.observe(event_id=str(uuid4()), attribute="last_update_status",
                               value=update, **base)
        return {"sampled": True, "function": function_name, "state": state,
                "last_update_status": update, "attested_by_aurora": False}
