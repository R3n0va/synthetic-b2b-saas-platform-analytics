# Customer success and support

This domain contains 7 governed business cases for the B2B SaaS platform.

| Case | Business question | SQL view | Decision |
|---|---|---|---|
| `BC022` | How is the customer base distributed across health segments? | `analytics.account_health_distribution` | renewal and service action |
| `BC023` | How much recurring revenue is exposed to renewal risk? | `analytics.renewal_risk` | renewal and service action |
| `BC024` | What ARR is due for renewal and how much is probability-weighted? | `analytics.renewal_pipeline` | renewal and service action |
| `BC025` | Do customer-success interventions improve account health? | `analytics.customer_success_intervention` | renewal and service action |
| `BC026` | Where are support response and resolution standards missed? | `analytics.support_service_levels` | renewal and service action |
| `BC027` | How does customer advocacy vary by market and segment? | `analytics.nps` | renewal and service action |
| `BC028` | Which reasons and churn types remove the most MRR? | `analytics.churn_reasons` | renewal and service action |

The machine-readable source of truth is `analytics/business_case_catalog.yaml`.
