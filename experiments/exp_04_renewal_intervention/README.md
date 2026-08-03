# Customer-success renewal intervention

**Experiment ID:** `EXP-04`  
**Randomisation unit:** `renewal_account`

## Hypothesis

A structured intervention for medium-risk accounts improves renewal and protects recurring revenue.

## Primary metric

`renewed`

## Guardrails

- `contraction_mrr_eur`
- `discount_cost_eur`

## Prespecified segments

- `account_segment`
- `health_band`
- `region_id`

## Decision rule

Launch when renewal improves and incremental protected ARR exceeds intervention and discount cost.
