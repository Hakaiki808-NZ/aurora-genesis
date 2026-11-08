# AWS private inference go-live verification — 8 November 2026 (NZDT)

## Current disposition

**Private research inference: LIVE AND VERIFIED on AWS.**
**Public beta, production-grade AI, and autonomous Aurora execution: NOT APPROVED.**

This document records what was actually tested. A **real Cognito hosted PKCE login**, signed ID token, and authenticated external API Gateway neural reply were verified on 8 November. This was a scripted HTTPS test, **not a rendered-browser sign-in / interactive UI acceptance test**. Neural answer quality is not yet production-qualified.

## Verified AWS resources (Sydney: ap-southeast-2)

| Service | Resource | Verified outcome |
| --- | --- | --- |
| Kyro web | CloudFront `E3P0BZ3PPWYCO`, `d3j65cc3p66kzr.cloudfront.net` | Enabled, Deployed |
| Kyro UI | S3 `v3/index.html`, `v3/neural.js` | Present; neural UI invokes `window.api('/neural/chat', 'POST', { message })` |
| CDN cache | Invalidation `I8JXOHMQIIENOVIATYLTUOZ05D`, path `/v3/*` | Completed |
| Kyro API | `kyro-v3-core-dev` / `GET /api/v3/health` | Direct Lambda API event returned HTTP 200 with `state: operational` |
| Neural HTTP API | `ces52hcf3e`, `GET /api/v3/neural/status` and `POST /api/v3/neural/chat` | Routes configured with API Gateway JWT authorizer |
| Neural backend | `genesis-neural-inference-dev` | Active, LastUpdateStatus Successful, 3,008 MB, 120-second Lambda timeout |
| Neural identity | Private Kyro Cognito pool (invitation only) | Pool/domain active; disposable account completed hosted PKCE and signed-JWT API acceptance; interactive browser UI not yet acceptance-tested |
| Neural budget | DynamoDB `genesis-neural-quota-dev` | Table ACTIVE; handler reports 10 attempts/user/day and 80 total/month |
| Kyro CC | `kyro-cc-control-v1` and private CloudFront distribution | Lambda Active; private distribution deployed; staff auth required |
| Aurora | `aurora-cloud-v1-controller-dev`, `aurora-cloud-v1-angel-dev`, `aurora-cloud-v1-motor-dev` | Lambdas Active; no claim of privileged production engine readiness |
| OSS source | PR #55, `deploy/oss/` | Self-hosted Ollama compose and unit tests merged; independent Docker execution not yet demonstrated |

## Actual generated responses (IAM-authorized Lambda test events)

Model reported: **Qwen2.5-0.5B-Instruct + experimental LoRA r2**.
The invokes were made via AWS Lambda Invoke, supplying **simulated API Gateway JWT claim structures**.
They demonstrate handler/model inference. The subsequent independent external HTTPS test below establishes a real JWT-authorized API request, but not an interactive browser session.

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
These *direct-Lambda* probes used synthetic test principal identifiers. External HTTPS authorization was separately verified with a real Cognito-signed token, as documented below.

## External HTTPS authentication and neural acceptance (same date)

A **disposable Cognito user** was created inside the existing private Kyro user pool with invite messages suppressed. A PowerShell HTTPS client on the existing SSM-managed AWS Windows instance performed a genuine hosted Cognito sign-in with **OAuth 2.0 authorization-code PKCE S256**, validated the returned OAuth state, exchanged the authorization code with its `code_verifier`, and received a Cognito-signed ID token with the **actual Kyro V5 client audience**.

Using that token as a bearer credential against the existing publicly reachable **JWT-protected** API Gateway routes:

| Check | External HTTPS result |
| --- | --- |
| Hosted Cognito login + PKCE state | `HOSTED_PKCE_LOGIN=PASS` |
| OAuth authorization code/token exchange | `OAUTH_TOKEN_EXCHANGE=PASS` |
| `GET /api/v3/neural/status` | **HTTP 200**; `genesis-neural-research` |
| `POST /api/v3/neural/chat` | **HTTP 200**, `chosen_action=neural_answer`, generated answer `READY` |
| Unauthenticated `GET /api/v3/neural/status` | **HTTP 401**, correctly protected |
| Public `GET /api/v3/health` | **HTTP 200** |
| CloudFront `/v3/index.html` and `/v3/neural.js` | **HTTP 200** each |

The temporary Cognito user was **deleted immediately after the successful test**; its password, authorization code and bearer tokens were never written to GitHub or test outputs. The live neural API remains invitation-only.

**Remaining limitation:** The test exercised the real Cognito hosted form, PKCE exchange, signature-validated JWT authorizer, Lambda and neural generation through live HTTPS endpoints, but used a scripted HTTP client instead of a graphical browser. Interactive JavaScript, page rendering, user-facing archived conversations and multiple-user isolation remain separate acceptance gates. The real deployed `/v3/neural.js` source is now version-controlled at `web/kyro/v3/neural.js` with an offline browser-script contract test.

## Activation and release gates that remain

1. **Browser acceptance:** PKCE and JWT-authorized external API Gateway requests are now verified using a disposable Cognito identity. An actual rendered-browser login and interactive neural UI response, plus archive/credential isolation, still require browser-level acceptance.
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
- [x] Real Cognito hosted PKCE -> signed JWT -> API Gateway -> model HTTP test verified
- [ ] Rendered-browser PKCE -> API Gateway -> model -> visible chat UI verified
- [ ] Neural instruction following and semantic routing benchmark gates passed
- [ ] Production/public beta approved

No new GPU instance or publicly accessible unauthenticated model endpoint was launched.
