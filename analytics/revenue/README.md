# Recurring revenue

This domain contains 7 governed business cases for the B2B SaaS platform.

| Case | Business question | SQL view | Decision |
|---|---|---|---|
| `BC001` | How did opening MRR move to closing MRR? | `analytics.monthly_mrr_bridge` | revenue planning |
| `BC002` | Which countries and regions produce recurring revenue? | `analytics.mrr_by_geography` | revenue planning |
| `BC003` | Which plans and customer segments drive MRR and seat economics? | `analytics.mrr_by_segment` | revenue planning |
| `BC004` | Are expansion and retention sufficient to protect the recurring base? | `analytics.revenue_retention` | revenue planning |
| `BC005` | How many paying companies are lost each month? | `analytics.logo_churn` | revenue planning |
| `BC006` | Where can add-on penetration be increased? | `analytics.add_on_attachment` | revenue planning |
| `BC007` | How dependent is the business on its largest accounts? | `analytics.revenue_concentration` | revenue planning |

The machine-readable source of truth is `analytics/business_case_catalog.yaml`.
