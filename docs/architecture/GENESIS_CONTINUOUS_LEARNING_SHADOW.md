# Genesis: consented memory, shadow testing and alignment candidates

**Status:** Private development experiment, not an autonomous self-training release.

## Boundaries

1. **Kyro** is the authenticated, consent-aware collection interface. No third-party or ChatGPT transcript capture occurs automatically. Only a connected relay or explicit per-turn submission can transmit ChatGPT messages to AWS.
2. **Genesis** receives a copy of each opted-in question in a *shadow* environment. A reference assistant response is labelled **unverified**. The Genesis base model and existing LoRA adapter answer the same question, with source/model/version metadata.
3. **Aurora** controls runtime isolation and authorization. The shadow harness cannot execute tools, change Engine authority, update production models, or approve its own training.
4. **Private AWS storage** holds questions, reference answers and comparison outputs. Public GitHub holds code only, never raw conversations or sensitive samples.
5. **Memory/RAG** can use reviewed project decisions immediately. **Weight training** requires separately curated, licensed/consented examples, held-out evaluations, regression and privacy checks, and manual promotion.

## Minimal acceptance gates

- Explicit opt-in for private conversational material; reject unknown consent and deletion requests must propagate to stored datasets and candidate queues.
- Filter secrets, identifiers and irrelevant personal details before any persistence or downstream export.
- Keep structured project *facts* distinct from user preferences, assistant suggestions and uncertain model-generated claims.
- Compare against a pinned, held-out benchmark, not by merely matching another model's wording.
- Record independent/human review, baseline vs adapter, regression, provenance, timestamp and immutable model lineage.
- Never train on benchmark answers, private material without permission, or data used for measuring improvement.
- Batch no more than eight questions and 128 generated tokens per response in the initial CPU evaluation.
- Account spending still requires active monitoring; AWS Budgets notifications are not hard caps. Initial evaluations must be few and bounded, not perpetual costly jobs.
- Fail closed on unavailable model, missing consent or invalid data; never fall back to fabricated inference.
- Keep development samples in private SSE-encrypted S3, rather than GitHub.

## Operational limitations

- A shadow test does not teach model weights. A completed adapter training run is a new *candidate* until independently evaluated and explicitly promoted.
- The existing approved-dataset daily checker is **separate** and can continue only on its human-approved synthetic dataset. Do not silently replace its approval manifest with chat transcripts.
- This ChatGPT session does not expose a persistent automatic webhook for every future conversation. Kyro must implement an opt-in capture relay for ongoing telemetry.
- Offline tests validate schema only. An AWS CodeBuild build and a verifiable result object are required before claiming a live Genesis shadow answer.
