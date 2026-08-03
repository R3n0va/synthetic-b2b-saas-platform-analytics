# Annual-plan discount framing

**Experiment ID:** `EXP-02`  
**Randomisation unit:** `eligible_account`

## Hypothesis

Showing annual savings in absolute EUR increases annual-plan selection without materially reducing expected first-year revenue.

## Primary metric

`annual_plan_selected`

## Guardrails

- `discounted_arpa_eur`
- `checkout_abandonment`

## Prespecified segments

- `country_code`
- `plan_id`
- `sales_motion`

## Decision rule

Launch only when conversion improves and expected first-year revenue remains non-inferior.
