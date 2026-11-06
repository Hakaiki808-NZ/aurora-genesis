# Genesis perception → cognition → AWS reference smoke: qualification report

**Date:** 7 November 2026 (NZDT)  
**Classification:** tested development integration, **not production deployment**, not evidence of AGI or consciousness.

## Working model integration

- `genesis/aws_perception.py`: read-only, IAM-backed AWS Lambda control-plane observations. Feature remains disabled until `GENESIS_AWS_PERCEPTION_ENABLE=1`.
- Only names explicitly listed in `GENESIS_AWS_ALLOWED_LAMBDAS` can be sampled by trusted in-process host code. Allowed region is set with `GENESIS_AWS_REGION`.
- Strict ARN match, approved AWS state enum, 45-second evidence TTL, one hashed source identifier and shared AWS control-plane provenance group.
- The adapter does **not** retain Lambda environment variables, code, IAM policies, credentials, tags or invocation payloads.
- `genesis/cognition_patch.py`: `What is the observed <attribute> for <entity>?` returns a conservative evidence summary; `contested`, `stale` and `unknown` do not invent a current value.
- Observations remain **separate** from normal fact memory, neural prompts and execution authorization. The answer is never promoted to verified training data.
- No public write endpoint or unrestricted user-triggered AWS API action has been added.

### Trusted host configuration

```bash
export GENESIS_AWS_PERCEPTION_ENABLE=1
export GENESIS_AWS_REGION=ap-southeast-2
export GENESIS_AWS_ALLOWED_LAMBDAS=kyro-v3-core-dev
# Python, in trusted server code only:
# genesis.sample_aws_lambda("kyro-v3-core-dev")
# genesis.respond("What is the observed state for aws_lambda:kyro-v3-core-dev?")
```

Use AWS role credentials with `lambda:GetFunctionConfiguration` scoped to allowed ARN(s). This is **not** a ChatGPT user tool and the server must independently authorize the caller.

## Independent GitHub validation

`python verify.py` runs the full historical regression suite plus `tests.awareness`, `tests.perception` and `tests.aws_perception_integration`. The new integration test covers feature-off behavior, allowlist rejection before SDK invocation, invalid identifiers, persistence of only safe state enums, private-field exclusion, evolving readings, observed-answer intent, disagreements and the no-training-data rule.

GitHub Actions `tests` and `Genesis neural adapter checks` succeeded on the integration development branch.

## Actual connected AWS checks — ap-southeast-2

### Live service baseline
- `kyro-v3-core-dev` returned HTTP 200 health with `state=operational`, `inference=genesis-research-reference`.
- `agk-kyro-beta` returned 401 on an unsigned test request: `Authenticated identity required`. Protected endpoints were not bypassed.
- Direct Bedrock `Converse` with `apac.amazon.nova-micro-v1:0`, `maxTokens=24`, returned `ThrottlingException: Too many tokens per day`.
- AWS Service Quotas currently lists zero relevant Nova Micro/Lite tokens and requests per minute in the account. Catalogue/profile `ACTIVE` is not evidence of invocation eligibility. No success claim for neural model inference.

### Private AWS proof-of-integration (CloudFormation)

Created stack: `genesis-perception-smoke-v01-stack`  
Created Lambda: `genesis-perception-smoke-v01` (Python 3.12, 128 MB, 18s timeout)  
IAM role: `genesis-perception-smoke-v01-role` — restricted to `kyro-v3-core-dev` Lambda `GetFunctionConfiguration` and `InvokeFunction`, plus its own CloudWatch logging  
Log retention: seven days  
Public Function URL: none; no API Gateway route.

The isolated smoke Lambda packages the **actual current `PerceptionCore` and `AwsLambdaStateAdapter` source** into CloudFormation inline code with a minimal in-memory test Store. It samples the real `kyro-v3-core-dev` control-plane state and invokes its public-health *handler* under IAM (without forging a JWT), then records observations and generates belief states.

**Actual Lambda invocation: PASS**
```json
{
  "test": "PASS",
  "aws_resource": "kyro-v3-core-dev",
  "live_lambda_state": "Active",
  "state_belief": "supported",
  "live_service_health": "operational",
  "inference_mode": "genesis-research-reference",
  "observation_events": 4,
  "sensor_attested_by_aurora": false,
  "bedrock_inference": "not_tested_quotas_zero",
  "deployment": "private_development_smoke"
}
```

This is a **live cloud integration test**, not a deployment of Genesis neural weights, not an authenticated user-chat/browser end-to-end test, and not proof that all code is in the production Kyro Lambda. The smoke Store is ephemeral; normal Genesis uses persistent SQLite.

## Remaining production gates

1. Confirm a nonzero Bedrock invocation quota, AWS access/IAM authorization, and a minimal successful constrained `Converse` call before any neural integration claim. Budget alerts alone do not enforce a hard spend ceiling.
2. Authenticate real public/sensor adapters, respect privacy/consent and data residency, and add Aurora-attested provenance when a real Aurora Engine source exists.
3. Stage validated Genesis runtime code into Kyro through a reviewed deployment pipeline. Test logged-in user flows, backups, migration, rollback, concurrency and retention before promoting to production.
4. Merge stacked PRs in order: Awareness Foundation → Perception/Belief Revision → AWS Integration; no silent merge to `main`.
5. Do not claim AGI, sentience, live weather sensing, trained weights or neural model success from this test.

## Maintenance
The dev smoke Lambda/stack is deliberately private and low-resource. It is safe to keep for bounded repeat tests; delete the CloudFormation stack and separately remove its IAM role when retired. Production services were not modified.
