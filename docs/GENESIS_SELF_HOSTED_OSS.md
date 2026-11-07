# Genesis — private self-hosted open-weight inference

**Status:** Deployable development configuration; no claim of live model generation until `smoke-test.sh` succeeds on the host. Bedrock is not involved.

## Architecture

```text
Kyro (authenticated UI)          Local-only Genesis API (port 8877)
         |                                |
    future private connector              v
                            Genesis cognition and Guardians
                                          |
                              Ollama (private Docker network)
                                          |
                              Licensed local open-weight model

Aurora (Engine) retains independent execution authority. Neural output is untrusted text.
```

## Quick start on a Docker host

From the repository root:

```bash
# Requires Docker Engine and Docker Compose v2, network for the first model pull.
docker compose -f deploy/oss/compose.yaml up --build -d
bash deploy/oss/smoke-test.sh
```

The stack runs three containers: Ollama, one-time model download, and the Genesis API. Ollama is **not** published to the host; Genesis binds **only** to 127.0.0.1:8877 by default. Models and Genesis state survive restarts in Docker volumes. The first pull can take time and requires Internet access. Inspect `docker compose -f deploy/oss/compose.yaml logs` if download fails.

The default small model is `qwen2.5-coder:1.5b` (previously tested through local Ollama). To choose another compatible model, set `GENESIS_OSS_MODEL` on the host **before** starting the stack, for example:

```bash
GENESIS_OSS_MODEL=qwen3:1.7b docker compose -f deploy/oss/compose.yaml up --build -d
# For gpt-oss 20B, only on sufficiently provisioned memory/accelerators:
GENESIS_OSS_MODEL=gpt-oss:20b docker compose -f deploy/oss/compose.yaml up --build -d
```

Do not run 20B/120B on underprovisioned systems: OpenAI recommends roughly 16GB memory for 20B and 80GB for 120B. Neither model is needed for the initial end-to-end proof. Check each model's licence before commercial deployment.

### Using the existing host Ollama installation instead of Docker

```bash
ollama pull qwen2.5-coder:1.5b
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
GENESIS_GENERATOR=ollama GENESIS_OLLAMA_MODEL=qwen2.5-coder:1.5b python3 serve.py
```

This existing host-only path binds 127.0.0.1:8766 and uses Ollama on 127.0.0.1:11434. Local Ollama runs with no Bedrock inference charges. It does consume local CPU/RAM and electricity.

## Production boundary

- **Do not publish ports 8877 or 11434 to the Internet**. The reference Genesis API has local administrative and data endpoints and is **not** a public authentication service. Route future access only through Kyro's tested JWT-authenticated private backend.
- Docker's application network keeps Ollama unpublished to the host and Internet. Outbound access is used during the initial weight download; restrict egress separately if your deployment requires it. Do not add public Ollama host ports.
- First-time downloads use Ollama's model registry; pin the image digest and model weight/hash for qualified production deployments.
- CPU generation may be slow, particularly on a 2GB server. AWS's existing t3.small is not a reliable deployment target for 20B/120B or larger models.
- Separate inference limits, log retention, backups, data privacy rules and evaluation gates still apply before public beta.
- This does not retrain models; knowledge modules, reviewed training and weight updates remain distinct workflows.

## Acceptance

Passing `docker compose config` and unit tests proves only the packaging and adapter behavior. **Working self-hosted neural inference** is established only when `deploy/oss/smoke-test.sh` returns `NEURAL_INFERENCE=PASS` from a real model response, followed by authenticated Kyro browser tests. No Aurora elevated execution is granted by this deployment.
