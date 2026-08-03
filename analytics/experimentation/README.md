# Experimentation

This domain contains 4 governed business cases for the B2B SaaS platform.

| Case | Business question | SQL view | Decision |
|---|---|---|---|
| `BC035` | Are variants balanced without duplicate assignments? | `analytics.experiment_assignment_integrity` | launch decision |
| `BC036` | Did assigned accounts receive the treatment? | `analytics.experiment_exposure` | launch decision |
| `BC037` | What is the primary, guardrail and revenue effect by variant? | `analytics.experiment_outcomes` | launch decision |
| `BC038` | Do experiment effects differ across countries and segments? | `analytics.experiment_segment_effects` | launch decision |

The machine-readable source of truth is `analytics/business_case_catalog.yaml`.
