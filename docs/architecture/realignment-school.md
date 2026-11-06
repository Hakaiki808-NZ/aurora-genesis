# Realignment School (Genesis pre-alpha)

**Status:** Working diagnostic prototype; **not neural retraining or AGI qualification**.

Realignment School sits inside Genesis's semantic learning and evaluation boundary. Aurora remains the operational engine and never receives semantic exercises or grants Genesis privileged execution. Kyro is the user-facing interface.

## Current scope
- Five fixed reference exercises: evidence, authority separation, untrusted content, regression and microphone privacy.
- Bounded scoring and corrective feedback, with deterministic tests.
- Per-batch deficit reports; failures can guide subsequent work.
- Model update and engine permission escalation are **not implemented**. `promote()` always rejects.

## Kyro AWS private beta
The hosted Kyro beta includes a separate Cognito-JWT-protected School API at `/api/v3/realignment/{status,curriculum,attempt,history,promote}`. Its serverless DynamoDB store partitions attempts by authenticated subject, expires practice records after 30 days, and does not store voice recordings. The cloud quiz is a diagnostic demonstration, not an in-model training loop.

## Voice interaction
Kyro uses a user-initiated browser speech-recognition adapter → existing authenticated Genesis chat → browser speech synthesis. Browser speech recognition may use the browser provider's processing services. No claim of a separately trained acoustic model. The microphone starts only after the user clicks Speak. Reply playback and automatic submission are optional and off by default. Browser support and real-user acceptance testing remain outstanding.

## Promotion gates (future)
1. Establish an independent benchmark and holdout cases.
2. Evaluate behavioural changes and regression rates.
3. Document source provenance, privacy and failure modes.
4. Obtain explicit human approval for weight/model artefact updates.
5. Deploy via Aurora's independent operational gates, with rollback.
