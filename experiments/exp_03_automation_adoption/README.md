# Automation adoption prompt

**Experiment ID:** `EXP-03`  
**Randomisation unit:** `account`

## Hypothesis

Contextual prompts after repeated manual workflows increase automation adoption and improve sustained usage.

## Primary metric

`automation_adopted_within_14_days`

## Guardrails

- `seven_day_active_account_rate`
- `prompt_dismissal_rate`

## Prespecified segments

- `plan_id`
- `feature_breadth_band`

## Decision rule

Launch when adoption improves with no meaningful active-account deterioration.
