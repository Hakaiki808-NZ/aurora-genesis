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
