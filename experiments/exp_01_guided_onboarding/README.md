# Guided onboarding checklist

**Experiment ID:** `EXP-01`  
**Randomisation unit:** `account`

## Hypothesis

A role-specific onboarding checklist increases 30-day activation without increasing onboarding support demand.

## Primary metric

`activated_within_30_days`

## Guardrails

- `onboarding_support_tickets`
- `cancellation_within_45_days`

## Prespecified segments

- `sales_motion`
- `account_segment`
- `country_code`

## Decision rule

Launch only when the lower confidence bound is positive and no material support guardrail deteriorates.
