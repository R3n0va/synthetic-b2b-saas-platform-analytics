# Metrics

The governed registry is `metrics/metric_definitions.yaml`.

## Recurring revenue

MRR is the sum of active recurring plan and add-on items for an account and month. Annual billing affects cash timing, not monthly recurring value.

```text
Opening MRR
+ New MRR
+ Expansion MRR
+ Reactivation MRR
- Contraction MRR
- Churned MRR
= Closing MRR
```

GRR excludes expansion. NRR includes expansion. Both use opening MRR as denominator.

## Account movement rules

- New: zero prior MRR, positive current MRR, no earlier active month.
- Reactivation: zero prior MRR, positive current MRR, active before.
- Expansion: positive MRR increase while remaining active.
- Contraction: negative MRR change while remaining active.
- Churn: positive prior MRR and zero current MRR.

## Product metrics

Active account requires observed product use, not only an active subscription. Seat utilisation compares active users with paid seats. Time to first value is the number of days from subscription start to first completed work order.

## Health score

The generated health score combines:

- usage and adoption: 50%;
- payment performance: 20%;
- support experience: 15%;
- customer relationship: 15%.

The score is descriptive and transparent. It is not a predictive model.

## Currency

Local amounts are converted to EUR using monthly rates. MRR and ARR are reported in EUR. Local amounts are retained for billing analysis.
