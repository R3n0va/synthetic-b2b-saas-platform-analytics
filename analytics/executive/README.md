# Executive reporting

This domain contains 3 governed business cases for the B2B SaaS platform.

| Case | Business question | SQL view | Decision |
|---|---|---|---|
| `BC039` | What changed in recurring revenue, retention, adoption and risk? | `analytics.executive_monthly_scorecard` | management review |
| `BC040` | What is the latest executive state of the business? | `analytics.latest_executive_scorecard` | management review |
| `BC041` | Which regions require management action? | `analytics.regional_operating_review` | management review |

The machine-readable source of truth is `analytics/business_case_catalog.yaml`.
