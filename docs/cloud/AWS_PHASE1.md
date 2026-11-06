# AWS cloud deployment — phase 1

**Status:** Infrastructure foundation only. This is **not** a deployed chat service or production launch.

## Region and spending controls

- Target: `ap-southeast-2` (Sydney). The New Zealand region `ap-southeast-6` is currently not enabled in the connected account.
- Existing AWS budget: US$1, with an email alert configured at a low absolute usage threshold. **Budgets do not cap spending.**
- Remaining promotional credit amount cannot be read through the connected role (organization policy denies `billing:GetCredits`).
- Do not launch an always-on EC2/ECS/Fargate/App Runner service or enable model inference without explicit spending guardrails.
- Keep all new foundation resources private and tagged. Never repurpose existing account infrastructure without identifying its owner.

## Deployable foundation

`infra/aws/foundation.yaml` creates only:

1. A private encrypted S3 artifact bucket with public access blocked;
2. An empty encrypted, immutable-tag ECR repository, basic on-push scanning and five-image retention;
3. A CloudWatch log group with seven-day retention;
4. A non-secret, Standard-tier SSM deployment-phase marker.

This infrastructure may still incur charges **if data is stored or logs are ingested**; the stack does not enforce a zero-dollar cap. No compute or public endpoint is created.

### AWS CLI

```sh
aws cloudformation validate-template \
  --template-body file://infra/aws/foundation.yaml \
  --region ap-southeast-2

aws cloudformation deploy \
  --template-file infra/aws/foundation.yaml \
  --stack-name aurora-genesis-dev-foundation \
  --parameter-overrides Stage=dev \
  --region ap-southeast-2 \
  --tags Project=aurora-genesis-kyro Environment=dev
```

Review `describe-stacks`, `list-stack-resources`, bucket public access, ECR encryption and AWS Cost Explorer after applying. No AWS account identifiers or secrets belong in GitHub.

## Architecture target (not deployed)

```text
User browser
  -> CDN + static Kyro web frontend
  -> Cognito unified identity / MFA
  -> API Gateway (JWT auth, throttling)
  -> Kyro backend (stateless, per-user isolation)
  -> Genesis cognition and policy services
  -> Aurora private execution authority (independent verification)
  -> controlled tools, memory and data
```

Additional products (developer API, community forum, administration and collaboration) should use the same identity provider, but have **separate authorizations and scopes**. Use DynamoDB only once the user/session schema and retention policy are tested. Use hosted models or Bedrock only behind per-request quotas and budget monitoring. The current localhost Kyro token is **not** cloud authentication; exposing it is prohibited.

## Mandatory gates before a reachable service

- Merge/review Genesis and Kyro alpha PRs; run the complete verification suite.
- Replace localhost shared token with OIDC authentication, multi-tenant authorization and secure sessions.
- Create/verify tenant isolation, rate limiting, audit logging and abuse controls.
- Confirm AWS credit eligibility, cost limits, billing alerts and a daily stop procedure.
- Red-team security boundaries, prompt injection and compromised-model behavior; keep proprietary Aurora separate.
- Prepare privacy notices, data retention, backup/recovery, incident response and rollback.
- Record reviewer approval before enabling public traffic.

## Deployment status

Foundation **template validated** by AWS CloudFormation in Sydney on 2026-11-06. Review the stack state independently before marking actual resource creation complete.
