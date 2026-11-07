# Kyro voice-first console (proposed, not deployed)

This frontend-only increment gives the authenticated Kyro V3 workspace a prominent voice console. It deliberately **reuses** the existing `school-voice.js` controls, chat transcript field and Genesis chat submit path rather than opening a second microphone or bypassing authentication.

## Behaviour
- The user explicitly presses **Talk to Kyro**, which opens the existing conversation pane and starts one speech-recognition session.
- Browser voice recognition populates the chat transcript; **auto-send stays opt-in** so transcription can be reviewed before it is submitted.
- Text-to-speech of Genesis replies is **on by default**, with a toggle.
- **Stop** uses the existing speech-stop handler.
- No OS command execution, privileged engine channel, persistent audio recording, new credentials, Cognito changes, or deployment changes are introduced.
- Browser speech recognition is not guaranteed offline and can send audio to a provider. Never describe this as private on-device recognition without a verified local engine.

## Review and test gates
1. Load `web/kyro/v3/index.html` via the Kyro V3 static site build or mirror it with the actual CSS/JS assets (the standalone HTML's absolute `/v3/` paths require that mapping).
2. Verify signed-out view has no active listening; sign in using existing Cognito.
3. Check mic permission denial, one-shot transcription, safe manual send, optional auto-send, reply TTS and Stop.
4. Test keyboard, mobile, speech-unavailable and permissions-failure states.
5. Confirm no request bypasses existing authenticated Kyro/Genesis APIs.
6. Release only after review; live CloudFront/S3 objects and the public-beta snapshot are untouched.

## Next implementation boundary
An actual OS-level, local-first voice default needs a dedicated native Kyro service for wake-word, STT, TTS and guarded intent dispatch. Aurora authorises runtime operations and Genesis handles reasoning. This browser panel is a safe first UI step, **not an OS-wide voice assistant**.
