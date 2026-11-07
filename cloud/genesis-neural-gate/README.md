# Genesis neural inference adapter — quota-gated AWS prototype

This is a private **development-only** adapter for the existing Kyro → Genesis
Lambda invocation contract. It uses a real *pretrained external* neural model
on Bedrock when enabled; it does not run Genesis-owned Qwen weights or alter
Aurora execution privileges.

The code is uploaded as CloudFormation inline Lambda source, with:
- strict off-by-default `GENESIS_NEURAL_ENABLED=0` feature gate;
- request shape and private Kyro invocation-context validation;
- no tool execution and no engine authority;
- atomic DynamoDB limit of 12 attempted model calls per UTC day;
- explicit Bedrock `maxTokens=128` and 1,800-character prompt limit;
- DynamoDB-atomic cross-worker call cap and a dedicated least-privilege IAM role;
- seven-day CloudWatch log retention; no prompt/response logging.

**Activation gate (not met)**: Sydney account had an effective daily Bedrock
Nova Micro token quota of **0**. An invocation with `maxTokens=16` returned
`ThrottlingException`. The cross-region TPM quota increase request
`55f3cefaa6b84c22b0cc7d71319ee9fctv6h3zGd` was submitted on
2026-11-07 and was **PENDING** on submission. The daily tokens cap was shown as
nonadjustable through Service Quotas, so this request alone might not permit
inference. Confirm both quotas and a successful live model probe before enabling.

The account's US$1 AWS budget is **alert-only**, not a hard cost cap.
The finite atomic request limit reduces risk but cannot guarantee a dollar cap
if AWS pricing changes. The previous project authorization was no more than
US$30 for experimental AWS model work; do not start continuously billable
resources without separate cost controls.

**Current production routing remains unchanged**: Kyro's authenticated
`POST /api/v3/conversations/{id}/generate` continues using the existing
research reference. When model quota and tests pass, update the *CloudFormation
template* for `kyro-v3-api-dev` to give the core Lambda invoke permission on
this adapter and set `KYRO_GENESIS_LAMBDA` to its ARN, while updating the chat
UI and response metadata to accurately identify the backend provider.
Do not hot-swap it before testing, and do not claim this Bedrock proxy is
running the Genesis-fine-tuned Qwen adapter.

In the meantime, Genesis's own Qwen2.5-0.5B CPU model weights and LoRA adapters
exist in a private S3 artifact bucket; they are **not** hosted for real-time
Kyro chat. Serving them requires a separate inference container/endpoint with
measured CPU memory and latency. Prior smoke tests were not standardized
accuracy benchmarks.

## AWS deployment and tests (2026-11-07)

- CloudFormation stack: `genesis-neural-gateway-dev` (**UPDATE_COMPLETE**).
- Private AWS Lambda: `genesis-neural-gateway-dev` (**Active**, no public API route).
- DynamoDB budget table: `genesis-neural-budget-dev`, on-demand.
- `action=status` returned 200, reporting the neural gate **disabled**.
- Synthetic chat invocation returned 503 (`neural_gate_closed`) with no Bedrock call.
- Atomic DynamoDB counter syntax was corrected to
  `SET expires = :ttl ADD attempts :one`, then the update succeeded.
- AWS Lambda reserved concurrency 1 was rejected because of the account's
  unreserved-concurrency minimum; the stack was redeployed **without**
  reserved concurrency. The DynamoDB atomic daily attempt cap is retained.
- Quota increase request status is now **CASE_OPENED**. The effective
  cross-region Nova Micro TPM quota and model daily token quota both remain
  **0**. The daily token quota is not adjustable through Service Quotas.

**Unresolved blocker:** AWS must grant usable Nova Micro quotas (including
daily tokens), or a separate CPU inference endpoint must be built for the
existing Qwen/LoRA artifacts. Until a successful real-model invocation,
leave `Enabled=0`. No claim of live neural chat.
