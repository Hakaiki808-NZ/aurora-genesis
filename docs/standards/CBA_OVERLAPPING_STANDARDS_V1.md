# Genesis standards ladder — overlapping C / B / A series

**Decision (8 Nov 2026):** Use a single progressive standards framework with
overlapping boundaries. This is an **evaluation/achievement taxonomy**, not
Aurora privileged execution authority.

## The three series

| Series | Meaning | Labels | Maturity |
| --- | --- | --- | --- |
| **C** | Minimum standards | C0 C1 C2 C3 C4 C5 | Baseline development/qualification targets |
| **B** | Achievable standards | B1 B2 B3 B4 B5 | Progressive, measurable improvement targets |
| **A** | Frontier / hypothesized upper standards | A1 A2 A3 A4 A5 | A1 maps to current frontier benchmark; A2–A5 are hypothetical research targets |

### Exact overlap

- **C5 ≡ B1**. The strongest C-level requirement is the entry to the B series.
- **B5 ≡ A1**. The top of the B series is the entry to the A series.
- Neither overlap is a new extra step: **16 labels, 14 distinct milestones**.
- Advancement order: `C0 → C1 → C2 → C3 → C4 → [C5=B1] → B2 → B3 → B4 → [B5=A1] → A2 → A3 → A4 → A5`.

The A1/B5 reference represents the **user-defined target** for the upper end
of today's model capabilities, not an independently verified fact about all
contemporary AI models and not proof of Genesis reaching that target.
Performance comparisons need a current, independently reproducible benchmark.

## Implemented reference

- `genesis/standards.py` provides immutable standard definitions, exact
  aliases, ordinal comparison, milestone criteria, and an evidence checklist.
- `Genesis.state()['standards_framework']` exposes the read-only taxonomy.
- `tests/test_standards_overlap.py` checks equivalence, exact rank ordering,
  A2–A5 hypothetical designation, and non-interference with Engine permissions.
- **No standard is automatically certified**. Attainment stays
  `UNVERIFIED` until a versioned independent protocol, held-out results,
  reproducible artifacts and reviewer record are supplied and assessed.

## Avoiding namespace collisions with earlier Aurora/Genesis code

The original project already used `C0..C5` as **execution capability ceiling
codes** in `genesis/capabilities.py`, `genesis/engine_boundary.py` and
the private Aurora C1 deployment. Those codes are a **legacy execution-policy
namespace**, *not* the new standards ladder's progression.

Until a versioned migration can rename that legacy namespace without breaking
signed requests, cloud configuration or compatibility, keep the concepts
strictly separate:

| Concept | Example | Who owns it | What it does |
| --- | --- | --- | --- |
| Standards achievement | `C5/B1`, `B5/A1` | Genesis evaluation and independent reviewers | Measures capability/quality |
| Legacy execution limit | `GENESIS_CAPABILITY_LEVEL=C4` | Genesis policy gate (not sufficient for execution) | Restricts what Genesis may request |
| Aurora execution admission | `execution_tier=C1` | Protected Aurora Engine | Authorizes or denies actual operations |

**Never accept a standard label as an Engine permission.** Reaching A1 or
a future A5 cannot install Motor handlers, unlock Supreme, disable Angels,
override human approvals or increase runtime authority.

Any future migration should introduce explicit names such as
`standard_target` and `execution_policy_tier` with backwards-compatibility
checks, while preserving the live C1 default-deny Engine gate.

## Next qualification work

1. Establish falsifiable evaluation criteria and measurement rubrics for C0–C5.
2. Attach held-out reproducible task results for C0 before certifying a tier.
3. Build B1–B5 test suites measuring generalization, task completion,
   calibration, robustness and safety against current external baselines.
4. Keep A2–A5 as hypotheses until independently testable criteria and
   evidence support their definition.
5. Qualify private Aurora execution permission tiers *separately*.

See [Aurora C0–C5 legacy execution contract](AURORA_C0_C5_CAPABILITY_CONTRACT.md)
for the independent authorization gates. Neither document claims live
deployment beyond Aurora C1.
