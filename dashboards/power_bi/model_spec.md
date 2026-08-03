# Semantic model

## Facts

| Table | Grain | Purpose |
|---|---|---|
| `mart.fct_account_mrr_monthly` | account × month | recurring revenue snapshot and movements |
| `mart.fct_invoice` | invoice | billing, payment and collection performance |
| `mart.fct_account_usage_monthly` | account × month | adoption, utilisation and operational value |
| `mart.fct_sales_funnel` | lead/opportunity | acquisition and pipeline conversion |
| `mart.fct_experiment_outcome` | assignment | experiment analysis |
| `core.renewals` | renewal | renewal pipeline and outcomes |

## Dimensions

`dim_date`, `dim_account`, `dim_country`, `dim_region`, `dim_plan`, `dim_channel`, `dim_segment`, `dim_sales_motion`, `dim_experiment`.

## Relationships

Use one-to-many, single-direction relationships from dimensions to facts. Keep the account-month revenue fact separate from invoice facts to prevent accidental mixing of recurring value and invoiced cash. Use a dedicated date role for activity, invoice, renewal and acquisition dates where required.

## Governance rules

- MRR comes from effective-dated recurring items, not invoice totals.
- ARR equals closing MRR × 12.
- NRR and GRR use the opening installed base only.
- Reported EUR uses governed monthly FX rates.
- Tax and one-off charges are excluded from recurring revenue.
- All executive totals must reconcile to `analytics.vw_executive_monthly`.
