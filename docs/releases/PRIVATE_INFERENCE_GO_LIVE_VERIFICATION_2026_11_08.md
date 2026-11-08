# AWS private inference go-live verification — 8 November 2026 (NZDT)

## Current disposition

**Private research inference: LIVE AND VERIFIED on AWS.**
**Public beta, production-grade AI, and autonomous Aurora execution: NOT APPROVED.**

This document records what was actually tested. It does **not** assert that a valid external
user successfully completed browser sign-in or that neural answers are production-quality.

## Verified AWS resources (Sydney: ap-southeast-2)

| Service | Resource | Verified outcome |
| --- | --- | --- |
| Kyro web | CloudFront `E3P0BZ3PPWYCO`, `d3j65cc3p66kzr.cloudfront.net` | Enabled, Deployed |
| Kyro UI | S3 `v3/index.html`, `v3/neural.js` | Present; neural UI invokes `window.api('/neural/chat', 'POST', { message })` |
| CDN cache | Invalidation `I8JXOHMQIIENOVIATYLTUOZ05D`, path `/v3/*` | Completed |
| Kyro API | `kyro-v3-core-dev` / `GET /api/v3/health` | Direct Lambda API event returned HTTP 200 with `state: operational` |
| Neural HTTP API | `ces52hcf3e`, `GET /api/v3/neural/status` and `POST /api/v3/neural/chat` | Routes configured with API Gateway JWT authorizer |
| Neural backend | `genesis-neural-inference-dev` | Active, LastUpdateStatus Successful, 3,008 MB, 120-second Lambda timeout |
| Neural identity | Private Kyro Cognito pool (invitation only) | Pool/domain active, authorizer attached, browser login not independently exercised |
| Neural budget | DynamoDB `genesis-neural-quota-dev` | Table ACTIVE; handler reports 10 attempts/user/day and 80 total/month |
| Kyro CC | `kyro-cc-control-v1` and private CloudFront distribution | Lambda Active; private distribution deployed; staff auth required |
| Aurora | `aurora-cloud-v1-controller-dev`, `aurora-cloud-v1-angel-dev`, `aurora-cloud-v1-motor-dev` | Lambdas Active; no claim of privileged production engine readiness |
| OSS source | PR #55, `deploy/oss/` | Self-hosted Ollama compose and unit tests merged; independent Docker execution not yet demonstrated |

## Actual generated responses (IAM-authorized Lambda test events)

Model reported: **Qwen2.5-0.5B-Instruct + experimental LoRA r2**.
The invokes were made via AWS Lambda Invoke, supplying **simulated API Gateway JWT claim structures**.
They demonstrate handler/model inference, **not** an external JWT signature validation or complete browser session.

- Prompt: `Respond with just the word READY.` -> answer `READY`,
  `chosen_action: neural_answer`, HTTP 200, ~26 seconds.
- Prompt: `Write one original five-word sentence about a lighthouse on Mars.` ->
  answer `A lighthouse stands sentinel over Martian sea, beacon of hope for explorers.`,
  `chosen_action: neural_answer`, HTTP 200, ~12.5 seconds.
  The answer exceeded the requested five words, an instruction-following failure.
- Prompt: `What is 2 plus 2? Reply with just the number.` -> HTTP 200
  but `chosen_action: recall_semantic` and **unrelated stored-knowledge text**,
  not an arithmetic result. This is a real regression, not a passing test.

A subsequent model-status request returned `model_loaded: true`.
The test prompts use synthetic test principal identifiers and should not be treated as
proof of Cognito browser sign-in or an authenticated public HTTP call.

## Activation and release gates that remain

1. **Browser acceptance:** real invited user's Cognito PKCE sign-in, JWT validation,
   status and chat calls, and archive/credential isolation must pass end-to-end.
2. **Neural correctness:** fix misleading `recall_semantic` routing for basic arithmetic,
   improve instruction adherence and run independent held-out QA/safety evaluations.
3. **Latency:** Lambda direct cold start took ~26 seconds for a short reply;
   HTTP API integration has a 30-second timeout, so cold/wider responses may time out.
   Verify real API latency rather than assuming Lambda success equals browser success.
4. **Public beta:** legal/privacy operations, backups, alert recipients, cost stop,
   JWT/MFA acceptance, and formal human review are not cleared.
5. **Aurora Engine:** privileged production actions remain restricted and must not
   be automatically enabled by model inference availability.
6. **Bedrock GPT-OSS 120B:** the separate Bedrock gateway still has
   `GENESIS_NEURAL_ENABLED=0` because the account has zero inference quota.

**Use the deployed private neural lab here:**
https://d3j65cc3p66kzr.cloudfront.net/v3/index.html

In the signed-in workspace: **Chat archive -> Genesis Neural Research**.
This panel is a separate live research experiment and does not persist answers
in the ordinary deterministic chat archive.

## Definition of done for this milestone

- [x] Public website origin and CloudFront enabled
- [x] UI model route and API JWT authorizer deployed
- [x] Actual OSS-weight neural generation verified through IAM-authorized AWS Lambda Invoke
- [x] Private read-only Kyro health route responds HTTP 200 in a direct Lambda test
- [x] CDN content refreshed
- [ ] Real external browser PKCE -> JWT -> API Gateway -> model -> UI verified
- [ ] Neural instruction following and semantic routing benchmark gates passed
- [ ] Production/public beta approved

No new GPU instance or publicly accessible unauthenticated model endpoint was launched.
