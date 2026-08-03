# Product adoption

This domain contains 7 governed business cases for the B2B SaaS platform.

| Case | Business question | SQL view | Decision |
|---|---|---|---|
| `BC015` | Which customer groups use the product actively? | `analytics.product_adoption` | product prioritisation |
| `BC016` | Where are customers paying for unused capacity? | `analytics.seat_utilisation` | product prioritisation |
| `BC017` | Does the product support completion of the core operational workflow? | `analytics.workflow_completion` | product prioritisation |
| `BC018` | Which onboarding tasks delay adoption? | `analytics.onboarding_completion` | product prioritisation |
| `BC019` | How long does it take a customer to complete its first real workflow? | `analytics.time_to_first_value` | product prioritisation |
| `BC020` | Which integrations are connected and actively used? | `analytics.integration_adoption` | product prioritisation |
| `BC021` | Which usage patterns precede churn? | `analytics.usage_before_churn` | product prioritisation |

The machine-readable source of truth is `analytics/business_case_catalog.yaml`.
