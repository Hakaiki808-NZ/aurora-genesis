# Kyro HTTPS site recovery — private-alpha operations

**Deployment verified 10 November 2026.**
This is stabilization of the existing Kyro private-alpha site, not a new
public self-registration launch or production-grade Genesis/Aurora release.

- CloudFormation stack (Sydney): \`kyro-platform-web-recovery-20261110\`
- Public landing: https://d397hqqvk3qah2.cloudfront.net/
- Invite-only workspace: https://d397hqqvk3qah2.cloudfront.net/v3/index.html
- CloudFront distribution: \`E1ICPPZNNKX0J6\`
- Private S3 origin bucket: \`kyro-platform-web-recovery-20261110-sitebucket-1pww4sctfu8n\`
- Infrastructure source: \`template.json\` (exported from the running stack).
- The previous Kyro CloudFront domain \`d3j65cc3p66kzr.cloudfront.net\`
  is **not** in the current AWS account's distribution inventory.
- The weather product has a **separate** CloudFront distribution; never
  redirect, modify, or delete it to serve Kyro.

## What was restored

- HTTPS CloudFront distribution and nonpublic AES256-encrypted versioned
  S3 bucket with full public-access blocking.
- Origin Access Control signed S3 requests; S3 bucket policy scoped to
  the exact CloudFront distribution ARN (no anonymous S3 reads).
- CloudFront security response headers, including HSTS, CSP, frame
  restrictions, no-referrer and nosniff. CSP explicitly allows only the
  pre-existing Kyro API origin and Cognito hosted domain for browser fetch.
- 31 existing static website and /v3 workspace assets. No application
  state or identity records were migrated.
- Existing invite-only Cognito private-browser app client's callback and
  logout allowlists now **include** the new /v3/index.html URL. Older
  URLs were preserved in the allowlist, not removed.
- Existing Kyro core HTTP API CORS allowlist includes the new CloudFront
  origin; JWT authorizers and protected API route definitions were not changed.

## Deploying new static content

Use an appropriately authorized AWS identity; these commands do not create
credentials. **Do not use --delete**, and do not upload private Aurora
engine files or user data.

\`\`\`bash
aws cloudformation describe-stacks --region ap-southeast-2 \
  --stack-name kyro-platform-web-recovery-20261110 \
  --query 'Stacks[0].Outputs' --output table

aws s3 sync cloud/public-site-v1/ \
  s3://kyro-platform-web-recovery-20261110-sitebucket-1pww4sctfu8n/ \
  --exclude 'README.md' --region ap-southeast-2

aws s3 sync cloud/public-beta-web/v3/ \
  s3://kyro-platform-web-recovery-20261110-sitebucket-1pww4sctfu8n/v3/ \
  --region ap-southeast-2

aws cloudfront create-invalidation --distribution-id E1ICPPZNNKX0J6 \
  --paths '/*'
\`\`\`

Before re-running infrastructure updates, review the CloudFormation change
set. Do not manually override the S3 bucket policy or Cognito identity
security settings. The bucket uses DeletionPolicy Retain.

## Public acceptance checks

Run from a machine with public internet access, or review GitHub Actions:

\`\`\`bash
python tools/aws_private_alpha_smoke.py
python tools/aws_public_beta_smoke.py
\`\`\`

The checks require 200 responses for the public landing, critical
assets, invite-only workspace static HTML and Kyro API health, and
401/403 responses for uncredentialed private operations. The public
beta smoke also checks CloudFront CSP and other security headers.

**These checks do not verify** Cognito PKCE in a real browser,
a complete authenticated create-conversation / generate / retrieve
round-trip, per-user isolation, private Cerebro access, or neural
model quality. Those require authorized invited test identities and
repeatable end-to-end acceptance before larger beta rollout.

## Current inference and security posture

The public Kyro health API reports \`genesis-research-reference\` and
\`aurora_execution: disabled\`. Aurora's independently protected
execution authority remains separate, and no JWT-bypass or research
neural-reasoning feature flags were enabled during site recovery.
The GPT-OSS and Qwen Bedrock on-demand quotas remain a distinct
inference dependency, not a blocker for serving the website itself.

Never call this public alpha site AGI, consciousness, production model
quality or a completed fully authenticated beta until independently verified.
