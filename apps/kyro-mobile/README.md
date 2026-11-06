# Kyro for iOS and Android — native private-alpha foundation

An Expo/React Native **TypeScript** client for the existing Kyro V5 private-alpha backend.
The mobile UI is native and shares the `/api/v3` API contract with the website; this is
not a WebView of the desktop UI. Aurora remains a distinct protected execution service.

## Setup
1. Install Node 22+, then run `npm install` from this directory and `npx expo install --check`.
2. Create a **public Cognito mobile app client** with authorization-code PKCE, no client secret,
   scopes `openid email profile`, and the exact callback `kyro://auth/callback`.
   Configure logout callback as needed. Do not alter existing web callbacks.
3. Copy `.env.example` to `.env` and replace the client ID with the **mobile** app client ID.
4. Test on development builds with `npx expo run:android` / `npx expo run:ios`
   (or Expo's managed build service); custom-scheme OAuth is not guaranteed in Expo Go.
5. Run `npm run check` and confirm backend auth, sign-in, projects, chat and collaboration
   on real Android and iOS devices before accepting this as a mobile beta.

## Current scope
- Cognito Hosted UI, authorization code with PKCE; ID token kept **only in memory**.
- Back-end `/me` session check; role-bound project lists; read-only file viewing;
  conversation creation/history/experimental Genesis responses; project discussions;
  read-only adapter status.
- No mobile autonomous runtime execution, token persistence, biometric login,
  deep-link allowlist handling beyond the Cognito redirect, push notifications or voice yet.
- OAuth is configured for private alpha. A placeholder/invalid client ID disables sign-in;
  full real-device OAuth flow is still unverified.
- Cloud API status and production readiness require separate real device/E2E verification.

The web-side `cloud/workspace-v5` changes are separate: CSS + web app manifest +
static-only service worker. No private Aurora code, signing keys or credentials are included.
