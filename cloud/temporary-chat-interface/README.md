# Kyro Temporary Chat Interface

A separate ChatGPT-style private browser interface for the existing Aurora + Genesis + Kyro workspace.

## Deployment

The files are hosted on the existing private-preview CloudFront distribution at
https://d3j65cc3p66kzr.cloudfront.net/temp-chat/index.html

They must be uploaded to the existing frontend S3 bucket under temp-chat/ with
Content-Type text/html, text/css and application/javascript respectively.
No production UI is overwritten. The existing Cognito browser client must include
the /temp-chat/index.html URL in both callback and logout URLs.

## Live backend

- Sign-in: Cognito OAuth2 Authorization Code + PKCE, with state and nonce.
- Tokens stay in JavaScript memory. PKCE verifier stays in tab sessionStorage only.
- Kyro API: GET /api/v3/health; GET/POST /api/v3/conversations;
  GET /api/v3/conversations/{id}/messages;
  POST /api/v3/conversations/{id}/generate.
- API always validates the JWT. No browser access to Aurora execution endpoints.
- The backend-generated text is **experimental Genesis research-reference** output,
  not evidence of a trained neural model or AGI.

## Interface features

Authenticated conversation history, new conversations, sending real server requests,
reply rendering, message copy, local JSON export, title search, responsive sidebar,
light/dark appearance, optional browser dictation, retryable network errors,
busy indicator, API health, and keyboard shortcuts.

## Limits

The current API responds synchronously: the typing indicator is a pending-request
indicator, **not** streamed tokens. The current backend has no documented delete,
rename or cancellation API, so those actions are intentionally absent. A queued
generation may continue server-side after a client timeout. Browser speech recognition,
where available, may rely on the browser vendor's speech service.

## Security

The temporary UI is invite-only because the API requires Cognito JWTs. The app
does not store tokens in localStorage. Static files contain no secrets. Do not use
this preview as a public production release without end-to-end authenticated testing,
accessibility testing, security review and model verification.


## Browser chat CORS fix (2026-11-07)

The existing API Gateway HTTP API has an authenticated catch-all route,
`ANY /api/v3/{proxy+}`. Browser calls with the Authorization header trigger
unauthenticated CORS preflight requests. The authenticated catch-all route
was returning HTTP 401 for requests matching its route.

The live API Gateway `ces52hcf3e` now also has:
`OPTIONS /api/v3/{proxy+}` with `AuthorizationType: NONE`
and target `integrations/563tava`, an AWS_PROXY integration to the dedicated
`kyro-temp-preflight-dev` Lambda created by the `kyro-temporary-chat-preflight-dev`
CloudFormation stack. The function returns HTTP 204 and cannot access chat,
Cognito tokens, or Aurora execution. API Gateway's existing CORS config
permits the CloudFront origin, authorization/content-type headers,
GET/POST/PUT/OPTIONS. The `$default` stage auto-deployed the new route.

**Carry this route into the CloudFormation/IaC ownership of the Kyro API.**
A stack deployment that removes unmanaged API routes may reintroduce the bug.
Do not remove JWT authentication from the ANY route.

Smoke test completed by invoking the core Lambda with an isolated synthetic
identity: create conversation returned 201, generate returned 200, and
GET messages returned two records (user and assistant). This tests the core
Lambda but not browser preflight, sign-in, or real network access. The real
browser end-to-end scenario still requires a signed-in test.

The current backend returns a research-reference answer; it does **not**
establish live neural inference or streaming generation.


### 2026-11-07 correction

The previous unauthenticated OPTIONS route was connected to `kyro-v3-core-dev`,
which intentionally returned HTTP **403** for OPTIONS requests. API Gateway
access logs confirmed these 403 preflight failures, so the browser could not
send authenticated conversation requests. The route now targets an isolated
204 responder (integration `563tava`), with a scoped Lambda invocation
permission for API Gateway and the original authenticated ANY route preserved.
The API Gateway `$default` stage has auto-deployed this change.

Verification: the new OPTIONS Lambda returned HTTP 204 to a synthetic event;
API Gateway route/integration/CORS/Cognito permissions were read back. **A
real browser preflight followed by a signed-in chat still needs user testing**.
