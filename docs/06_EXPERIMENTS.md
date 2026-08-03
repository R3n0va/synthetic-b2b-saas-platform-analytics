# Experiments

## Data model

Assignment, exposure and outcome are separate tables. An assigned account is not automatically treated as exposed. Analyses use exposed assignments for treatment-effect estimates and retain the assignment population for integrity checks.

## Designs

### Guided onboarding checklist

- Unit: account
- Primary: 30-day activation
- Guardrail: onboarding support tickets
- Decision: launch only when activation improves without operational burden

### Annual-plan discount framing

- Unit: self-service account
- Primary: annual-plan selection
- Guardrail: discounted ARPA
- Decision: consider both conversion and revenue dilution

### Automation adoption prompt

- Unit: active account
- Primary: automation adoption
- Guardrail: seven-day retention
- Decision: launch when adoption improves without reducing continued use

### Customer-success renewal intervention

- Unit: medium and larger account
- Primary: renewal
- Guardrail: contraction
- Decision: evaluate renewal lift against commercial concessions and capacity

## Decision rules

The Python report estimates absolute and relative effects, a 95% confidence interval and a two-sided p-value. Outputs are labelled `LAUNCH`, `DO NOT LAUNCH` or `INCONCLUSIVE`. Segment results are diagnostic and are not treated as independent primary tests.
