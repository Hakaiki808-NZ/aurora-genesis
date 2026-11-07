# Genesis — GPT-OSS 120B model selection

Date: 2026-11-08 (NZDT)
Status: **model selected, AWS inference blocked; gated source integration only**

## Decision

Use OpenAI GPT-OSS 120B as the selected pretrained reasoning backend for Genesis V1 through Amazon Bedrock in `ap-southeast-2` (Sydney). Exact model ID: `openai.gpt-oss-120b-1:0`.

- Genesis remains the model/cognition system; the pretrained model supplies optional neural text generation, not Aurora Engine authority.
- Kyro remains the interface. Do not claim the public/invite-only website uses this model until verified end-to-end.
- This is a selected externally pretrained open-weight model, **not** a Genesis-trained foundation model or a new checkpoint.
- Do not silently fall back to another paid foundation model. Existing deterministic/symbolic pathways remain available while the neural gate is disabled.

## Verified evidence on 2026-11-08

1. AWS identity was authenticated via the connected AWS environment.
2. Sydney Bedrock `ListFoundationModels` returned `openai.gpt-oss-120b-1:0`, provider OpenAI, lifecycle ACTIVE, text output, ON_DEMAND.
3. `GetFoundationModel` confirmed the model ARN `arn:aws:bedrock:ap-southeast-2::foundation-model/openai.gpt-oss-120b-1:0`, with streaming support.
4. A bounded `Converse` probe (`maxTokens=80`) **failed** with `ThrottlingException: Too many tokens per day`. No successful generated text was received.
5. `ListServiceQuotas` in Sydney reported **0** on-demand requests/minute (`L-25B50707`) and **0** tokens/minute (`L-9DC5F595`) for OpenAI GPT OSS 120B; both were `Adjustable=false`. These entries are not automatically evidence of an adjustable quota-increase pathway.
6. The existing `genesis-neural-gateway-dev` Lambda was ACTIVE but configured with `GENESIS_NEURAL_ENABLED=0` and the older Nova Micro model before this code selection.

## Source configuration

```bash
export GENESIS_GENERATOR=bedrock
export GENESIS_BEDROCK_MODEL_ID=openai.gpt-oss-120b-1:0
export GENESIS_BEDROCK_REGION=ap-southeast-2
export GENESIS_BEDROCK_MAX_TOKENS=256
export GENESIS_BEDROCK_MAX_CALLS=8
# Do not enable until both quota and successful smoke-test gates pass:
export GENESIS_BEDROCK_ENABLE=0
```

The CloudFormation template selects GPT-OSS 120B via `GENESIS_NEURAL_MODEL_ID`, restricts the IAM model ARN, and preserves `Enabled=0`. Keep the private per-day DynamoDB attempted-call cap and avoid logging raw prompts or responses.

## Activation gates

- [ ] AWS Support/account admin resolves applicable GPT-OSS 120B inference quota and confirms permitted usage.
- [ ] Bounded actual Bedrock `Converse` smoke test succeeds using the selected model and region.
- [ ] Verify private Lambda IAM permissions, service budget/alerts and model-specific usage/cost reporting.
- [ ] Pass no-cloud-cost Genesis regression and neural adapter tests.
- [ ] Deploy updated CloudFormation template with `Enabled=0` initially, verify stack state and private status.
- [ ] After controlled enablement, verify authenticated Kyro → Genesis chat in a real browser before changing mainline routing.
- [ ] Keep Aurora Engine authority and side effects outside the neural adapter.

## Cost and licensing

Bedrock invocation is metered. The open-weight model licence does not make AWS inference free. No reserved instance, provisioned throughput, public endpoint, training job, or recurring GPU resource is authorised by this model selection alone.
