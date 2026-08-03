# Billing and collections

This domain contains 6 governed business cases for the B2B SaaS platform.

| Case | Business question | SQL view | Decision |
|---|---|---|---|
| `BC029` | Which payment methods and markets have the strongest success rates? | `analytics.payment_success` | collections and payment operations |
| `BC030` | How much failed revenue is recovered through retries? | `analytics.payment_recovery` | collections and payment operations |
| `BC031` | Which dunning step and channel recover invoices? | `analytics.dunning_effectiveness` | collections and payment operations |
| `BC032` | Where is cash collection risk concentrated? | `analytics.overdue_receivables` | collections and payment operations |
| `BC033` | Which segments generate the highest commercial adjustments? | `analytics.refunds_and_credits` | collections and payment operations |
| `BC034` | Do invoice headers reconcile to invoice lines? | `analytics.invoice_reconciliation` | collections and payment operations |

The machine-readable source of truth is `analytics/business_case_catalog.yaml`.
