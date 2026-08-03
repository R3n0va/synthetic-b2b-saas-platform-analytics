# Sales and acquisition

This domain contains 7 governed business cases for the B2B SaaS platform.

| Case | Business question | SQL view | Decision |
|---|---|---|---|
| `BC008` | Where does conversion differ by market, channel and sales motion? | `analytics.sales_funnel` | commercial allocation |
| `BC009` | Which commercial segments win most consistently? | `analytics.opportunity_win_rate` | commercial allocation |
| `BC010` | Where are sales cycles longest? | `analytics.sales_cycle` | commercial allocation |
| `BC011` | Which partners generate durable recurring revenue? | `analytics.partner_performance` | commercial allocation |
| `BC012` | How quickly do self-service trials become paid? | `analytics.trial_conversion` | commercial allocation |
| `BC013` | How is the contract base split by billing frequency and term? | `analytics.contract_mix` | commercial allocation |
| `BC014` | Which market-channel combinations acquire customers efficiently? | `analytics.marketing_efficiency` | commercial allocation |

The machine-readable source of truth is `analytics/business_case_catalog.yaml`.
