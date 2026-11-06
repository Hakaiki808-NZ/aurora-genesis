# Research: AI features people most want, November 2026

Scope: a practical prioritisation for Genesis/Aurora/Kyro; **not** a universal
ranking or proof that any particular capability is completely unavailable.
Some assistants already have partial implementations. Numbers below refer to
different surveys, populations, dates and question wordings: do not compare
them as if they came from a single poll.

| User demand | Public evidence | Engineering response |
|---|---|---|
| Problems solved rather than plausible replies | Alchemer 2026: 37.9% selected faster issue resolution; 23.7% wanted less repetition in customer-service interactions | Define measurable completion criteria, durable task state, evidence review |
| Proactive assistance | Prophet 2026: 62% expressed interest in AI that notices relevant things and proactively helps | Pull-only attention/due feed; later opt-in scheduling by Kyro |
| Better decisions and planning | Kantar: 45% want decision support, 42% financial planning/budgeting | Decision support first, not autonomous buying or financial actions |
| Trustworthy answers | Gartner September 2025: 53% distrust or lack confidence in AI-generated summaries | Evidence references, explicitly unverified claims, reviewer decision |
| User control | Pew September 2025: roughly 60% want more control over how AI is used in their lives | Explicit approval of tasks, human-attested completion, no automatic external execution |
| Responsible delegation | Ping Identity 2026: 71% concerned an AI agent might misrepresent their values | Keep external action authority with Aurora; no automatic delegation |
| Personalised memory | Alchemer 2026: less repetition and personalisation both drew 23.7% | Existing Genesis episodic/fact memory; future explicit user-controlled memory UI |

Sources:
- Alchemer 2026 AI and Customer Expectations Report:
  https://www.alchemer.com/resources/benchmark-report/ai-and-cx-customer-expectations-report-2026/
- Prophet 2026 AI-powered consumer report:
  https://prophet.com/2026/04/the-2026-ai-powered-consumer-report/
- Kantar Global Consumers and AI Assistants:
  https://www.kantar.com/inspiration/research-services/leveraging-ai-assistants-pf
- Gartner consumer distrust of AI search, 3 September 2025:
  https://www.gartner.com/en/newsroom/press-releases/2025-09-03-gartner-survey-finds-53-percent-of-consumers-distrust-ai-powered-search-results0
- Pew 17 September 2025:
  https://www.pewresearch.org/science/2025/09/17/how-americans-view-ai-and-its-impact-on-people-and-society/
- Ping Identity 2026 Consumer Survey:
  https://www.pingidentity.com/en/lp/4423-2026-consumer-survey-ai-trust.html

## Decision

Build the narrow **Outcome Assurance v0** foundation before attempting a
fully autonomous general-purpose agent. AI agents still frequently fail at
long-horizon real-world tasks; a task should never be marked completed merely
because a model generated a convincing account of its work.

Implemented in this branch:
- User-declared success criteria and stored status with restart persistence.
- Human review of referenced evidence against each criterion.
- Explicit completion confirmation, labelled *human-attested*, not independently verified.
- Pull-only due and attention feeds for a Kyro dashboard.
- Separate token-gated control endpoints; no direct tool execution and no Aurora bypass.

Remaining gaps (no completion claims):
- Actual background scheduler/push notifications and user opt-in.
- Independently authenticated reviewer identity (Kyro must own).
- Cryptographically verified Aurora receipts bound to evidence.
- Source citation inspection and external fact-checking.
- Fine-grained consent/revocation for personal memory.
- Browser/computer-use execution with robust rollback, bounded budgets and
  consequential-action approvals.
- End-to-end integration with Kyro and live AWS, including threat model testing.
