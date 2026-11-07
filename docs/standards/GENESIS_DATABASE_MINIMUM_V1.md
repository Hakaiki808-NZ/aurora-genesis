# Database Minimum Standard V1 — Aurora / Genesis / Kyro

**Goal:** A usable, secure, invite-only AWS platform with persistent conversations, source-attributed public knowledge, safe model retrieval and independently testable endpoints.

**Scope lock:** Aurora retains execution authority; Genesis owns cognition, model memory and retrieval; Kyro owns user-facing HTTP routes and accounts. Public source text has no engine, guardian, policy or tool authority.

## Mandatory acceptance gates

| Gate | Minimum evidence for PASS | Current state |
|---|---|---|
| Identity | Cognito JWT authorizer on tenant routes; missing/invalid JWT rejected | Existing Kyro authorizer; signed-in test pending |
| Tenant separation | Verified subject and tenant isolation for messages, teams, memories and files | Cross-tenant tests pending |
| Conversations | Create, append, list, resume and durable idempotent writes | Existing Kyro V3 implementation; signed-in roundtrip pending |
| Public knowledge | Three bounded, vetted metadata connectors with provenance | Implemented in candidate deployment |
| Model boundary | External text is treated as untrusted reference data | Separate retrieval-only endpoint |
| Schema | Explicit keys, constraints, TTL and retry behaviour | Public metadata table pk/sk |
| Data rights | Fixed source allowlist; field-level exclusion of copyrighted abstracts | Metadata-only policy |
| Search | Bounded term index and retrieval without paid vector services | Limited English-first retrieval |
| Data quality | Dedup by external ID, canonical source URL, licence and expiry | Implemented in candidate deployment |
| Backup / recovery | DynamoDB PITR plus verified restore | PITR provisioned; restore drill pending |
| Secrets | No hardcoded secrets; encrypted data; least privilege | AWS IAM/template review pending |
| Observability | Health, failure logs, short retention, no private query logging | Lambda/CloudWatch design |
| Availability | Real signed-in HTTP tests and one persisted knowledge roundtrip | Pending |
| Neural inference | Real neural inference with measured quota and quality | BLOCKED: Bedrock quota |
| Weight training | Rights-reviewed dataset, eval, rollback and enforceable cost gate | DISABLED |
| Release | CI, threat model, full browser test, documented rollback | NOT PRODUCTION READY |

No gate passes solely because a CloudFormation stack is CREATE_COMPLETE.

## Data responsibilities

- Existing Kyro DynamoDB tables: user, workspace, conversation, audit and migration state. Never mix tenant conversations with public reference metadata.
- Genesis public metadata: source records use SOURCE#source / DOC#sha, and retrieval index records use TERM#word / HIT#source#sha. Metadata has a 30-day TTL.
- Access counters use hashed Cognito subject references and a 48-hour TTL. No raw chat prompts are intentionally stored in the metadata table.
- Local Genesis SQLite remains suitable for standalone research, not as the hosted multi-tenant chat database.
- Future approved training datasets belong in an immutable and access-restricted S3 registry, with source rights, hash, collection timestamp, PII scan, evaluation split and model lineage. This pipeline is not enabled.
- Vector search is deferred until semantic retrieval and pricing benchmarks justify it.

## Vetted public sources

| Source | Ingested fields | Rights boundary |
|---|---|---|
| OpenAlex | Work ID, title, publication year and record URL | CC0 metadata; respect usage quotas |
| Wikidata | Entity ID, label, description and URL | CC0 structured data |
| Crossref | DOI, title and DOI URL | Bibliographic facts only; exclude abstracts |

Public accessibility does not automatically mean unrestricted training permission. Wikipedia prose, arXiv full text, Common Crawl pages and arbitrary model-hosting datasets require separate licensing and privacy checks. Retrieval is not neural-weight training.

## Operating limits

- Existing invite-only Cognito JWT auth. No new anonymous API.
- Fixed upstream domains only, no generic URL fetching or crawling.
- Search: up to five results, 120-character queries, up to eight indexed terms, 30 external lookups per identity per UTC day, reject obvious email or phone strings.
- Upstream timeout 5 seconds, response cap 200 KB, metadata expiry 30 days, DynamoDB on-demand, PITR and seven-day CloudWatch retention.
- Do not promote public source instructions into policies or make model weight updates from fetched text.
- Cost alerts are not spending caps; no GPU, unbounded batch, or scheduled retraining in this phase.

## Definition of done

**Usable private alpha:** verified sign-in; conversation persistence and generation; licensed source query from all three providers; local search; cross-tenant denial; recovery; throttling; endpoint health; clean rollback.

**GPT/Claude-level service:** additionally requires tested neural inference, appropriate inference capacity, streaming, formal quality/safety evaluation, rate limits, monitoring, browser testing and scalable reliability. No equivalence claim is made.

**Deployment note:** The first attempt at kyro-knowledge-standard-v1-dev was rolled back because account Lambda unreserved concurrency cannot be reduced below 10. The reserved-concurrency property was removed from the template; the retry must be independently tested.
