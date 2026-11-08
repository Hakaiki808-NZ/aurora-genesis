# ARC-AGI-3 Genesis evaluation readiness — 7 November 2026

Status: benchmark integration code prepared, synthetic tests pending CI; **no ARC score or live Genesis model evaluation has been recorded by this change.**

## Purpose

Test actual Genesis decision-making against the official interactive ARC-AGI-3 game SDK, not a copied score, hardcoded solution, generic external AI, or random-agent fallback.

The runner lives at tools/benchmarks/arc_agi_3.py. It obtains observation frames, asks Genesis for one action, enforces the published action constraints, sends the action to the official SDK, and records status, attempted actions, official score availability, runtime, and provenance.

## Trust boundaries

- LOCAL REFERENCE: imports the public Genesis v0.1 class with an isolated temporary database and disables all external text generation. **Not a neural model or AWS result.**
- PRIVATE KYRO HTTPS: requires an explicit authorized HTTPS route and short-lived bearer token. Responses must use the Genesis API chat envelope, with the answer containing exactly an allowed ARC action JSON object. Results are explicitly labelled as **unverified remote model provenance** until an independently tested checkpoint/backend identity is obtained.
- Aurora remains the execution authority and is never given new powers by these games. Game actions have no shell, tool or file-write authority outside the official ARC environment. Invalid model output blocks rather than substituting random actions.
- The ARC official SDK is the environment and scorer; synthetic tests never count as scoring evidence. Record the actual agent source SHA, any cloud model checkpoint hash and official scorecard/replay separately.

## Commands

Synthetic tests (no network, no AWS charges):
- python3 -m tests.arc_agi_3_harness
- python3 -m tools.benchmarks.arc_agi_3 --output /tmp/arc-agi-3-check.json

The second command intentionally records BLOCKED unless the --live flag is set.

Public ARC SDK guest-mode smoke test (non-competition; only if SDK/network are available):
- Install Python 3.12 and arc-agi==0.9.9.
- The official toolkit documents anonymous access to public games. Explicitly opt in using `--live --arc-anonymous` and record `arc_access_mode=anonymous_public`.
- Guest SDK gameplay is not evidence of scored competition participation, private Kyro authentication, or Genesis neural capability. It still requires a functioning Genesis agent and action contract.
- Private Kyro HTTPS always requires its own short-lived bearer token; `--arc-anonymous` does **not** bypass it.
- Example: `python3 -m tools.benchmarks.arc_agi_3 --live --arc-anonymous --agent kyro-https --game ls20 --max-actions 8` (requires `KYRO_ARC_URL` and `KYRO_ARC_TOKEN`).

Real ARC API test of Genesis symbolic reference (not AWS):
- Install Python 3.12 and arc-agi==0.9.9.
- Supply an ARC_API_KEY from the official ARC Prize service in your environment.
- python3 -m tools.benchmarks.arc_agi_3 --live --agent local-reference --game ls20 --max-actions 8

Real private AWS-Kyro test (only after endpoint contract, model and security verification):
- Set ARC_API_KEY (official ARC credential), KYRO_ARC_URL (private HTTPS Genesis chat URL), and KYRO_ARC_TOKEN (short-lived bearer credential) using a secure secret store.
- python3 -m tools.benchmarks.arc_agi_3 --live --agent kyro-https --game ls20 --max-actions 8
- Never commit tokens or model prompts/results containing private user data.

## Acceptance gates

- [ ] Real ARC API key supplied.
- [ ] Working authenticated Kyro/Genesis action-response path proved without synthetic JWTs.
- [ ] Live neural backend identity, trained checkpoint provenance/hash, and no fallback to external pretrained provider demonstrated.
- [ ] Official ARC gameplay with action logs and a valid scorecard archived.
- [ ] Aurora containment and resource controls separately verified.
- [ ] Cost caps, quota admission, alert destinations and independent stop tested. The AWS USD 1 budget is only an alert.
- [ ] Repeat on held-out games; distinguish normal mode from competition mode and never train on test solutions.

Known limitations: As inspected on 7 November 2026, AWS Sydney has a Genesis Neural Gateway Lambda with GENESIS_NEURAL_ENABLED=0 and Bedrock Nova Micro quotas of 0. A deployed Genesis CPU inference image exists, but neither its benchmark action contract nor a truly independently trained Genesis neural model was verified. The first live test must not be described as complete until the actual official outcome exists.

Official references: https://github.com/arcprize/ARC-AGI and https://github.com/arcprize/arc-agi-3-benchmarking and https://docs.arcprize.org/

## Manual GitHub launch gate

After merging this change to main, find the GitHub Actions workflow named ARC-AGI-3 readiness and manually gated live test. Its default dispatch runs synthetic checks only. To authorize a real game choose run_arc_live=true, specify the game (initially ls20), and ensure the repository Actions secrets ARC_API_KEY, KYRO_ARC_URL, KYRO_ARC_TOKEN are supplied from approved secret management. The live job runs from main only, requires all three secrets, caps gameplay at eight actions and uploads a seven-day labelled result artifact. It will fail closed if the private chat route is absent, unauthenticated, does not emit ARC action JSON, or the ARC service cannot return observations. Passing CI alone does not complete the authentication, model identity or cost-stop acceptance gates.
