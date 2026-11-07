# Genesis public metadata retrieval — private Kyro AWS integration

This isolated Lambda/DynamoDB service provides **live and cached, attributed public metadata** for Genesis reference retrieval. It does NOT train neural weights or connect to Aurora operational authority.

## AWS state (2026-11-07)

- Stack: kyro-knowledge-standard-v1-dev in ap-southeast-2: CREATE_COMPLETE after correcting an account-level reserved-concurrency conflict.
- Table: kyro-knowledge-standard-v1-dev-store, PAY_PER_REQUEST, SSE ENABLED, PITR ENABLED (35 days).
- Function: kyro-knowledge-standard-v1-dev-knowledge, Python 3.12.
- Existing HTTP API: ces52hcf3e. JWT authorizer: the existing Kyro V3 authorizer; no new public signup.
- AWS Lambda direct smoke tests passed: unauthenticated context rejected (401), sources and health (200), one live metadata result each from OpenAlex, Wikidata and Crossref (200), and cached search returning all three sources (200).
- Important: direct Lambda tests are not a signed-in browser/API Gateway integration test. CloudFormation creation is not proof of end-to-end production readiness.

## Routes

All endpoints are GET requests under the existing authenticated HTTP API:

| Path | Behaviour |
|---|---|
| /api/v3/knowledge/health | Health and schema state |
| /api/v3/knowledge/sources | Source names, licences, terms links |
| /api/v3/knowledge/search?q=climate&source=openalex&limit=2 | Fetch bounded live public metadata and cache it |
| /api/v3/knowledge/cache/search?q=climate&limit=5 | Search locally cached public metadata |
| /api/v3/knowledge/training/status | Explicit status: neural weight training disabled |

Base URL: https://ces52hcf3e.execute-api.ap-southeast-2.amazonaws.com

A valid Kyro Cognito JWT must accompany requests, supplied via Authorization: Bearer TOKEN. Do not place real credentials in public issue reports or the repository.

Example (replace TOKEN with your existing invited-user access token):

    curl -H "Authorization: Bearer TOKEN" "https://ces52hcf3e.execute-api.ap-southeast-2.amazonaws.com/api/v3/knowledge/sources"

## Reproducible deployment

From repository root with Python 3.12, boto3 and an already-authorized AWS identity:

    python tools/aws/deploy_knowledge_service.py --api-id YOUR_API_ID --jwt-authorizer-id YOUR_AUTHORIZER_ID
    python tools/aws/deploy_knowledge_service.py --api-id YOUR_API_ID --jwt-authorizer-id YOUR_AUTHORIZER_ID --apply

The first command validates only. The second creates or updates the stack. It does not provision Cognito, public users or additional neural compute. Source code is injected into the CloudFormation inline Python Lambda package, avoiding untracked ZIP upload steps.

Run standalone contract checks:

    python -m unittest tests.knowledge_service_contract -v

## Safety and limits

- The Lambda verifies JWT claims are present; the existing API Gateway verifies token authenticity. Direct Lambda invocation can spoof a context and is **not** a substitute for gateway authentication testing.
- Searches are bounded to five records, 120 characters, 30 external requests per Cognito subject per UTC day, and small 200 KB upstream responses.
- The only external hosts are api.openalex.org, www.wikidata.org, and api.crossref.org, each assembled from known endpoints. User-provided URL fetches are not implemented.
- Crossref abstracts, scholarly full texts, arbitrary crawled pages, private chats and user-submitted documents are not captured for training.
- Provenance, trust status, expiry and explicit training_eligible=False are stored with each record.
- Cache is a bounded English-first token index, not semantic vector retrieval.
- Upstream outages return 502, metadata database failure 503; no automatic retraining, payment, external tool execution or Aurora authority.
- PITR is enabled, but a restore drill is still required. AWS billing alerts are not spend caps; monitor cost and review before any scale-up.

## Required follow-up acceptance

Verify a real invited Cognito user can sign in and call all five routes through API Gateway; test CORS in Kyro; verify cross-user isolation for the existing private state and conversations; perform restore drill; demonstrate neural model inference with approved capacity; run end-to-end browser conversation generation and persistence; review threat model and costs before external beta.
