# Power BI Implementation

The dashboard uses PostgreSQL analytical views as its preferred source. CSV reports can be used for a portable prototype.

## Import order

1. Date dimension
2. Account dimension
3. Geography and plan dimensions
4. Account-month fact
5. MRR movements
6. Invoice-payment summary
7. Renewal pipeline
8. Experiment outcomes

## Validation

Before publishing:

- closing MRR must match `analytics.monthly_mrr_bridge`;
- active-account count must match `mart.account_month`;
- invoice and payment totals must match PostgreSQL views;
- latest-month risk MRR must match `analytics.renewal_risk`;
- experiment variant counts must match assignment and exposure views.

The full page design and DAX library are in `dashboards/power_bi/`.
