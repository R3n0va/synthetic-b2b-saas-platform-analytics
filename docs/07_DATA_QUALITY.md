# Data quality

## Python controls

Validation is generated from the governed schema registry and supplemented with business rules. The verified smoke execution performs 531 checks because each contracted column is validated individually in addition to table, key, relationship and reconciliation checks.

Blocking failures include:

- missing table or column;
- invalid logical type;
- null or duplicate primary key;
- orphaned foreign key;
- invalid contract, subscription, user or work-order chronology;
- negative recurring revenue or usage counts;
- invoice and invoice-line arithmetic mismatch;
- payment linked to a failed attempt;
- score outside its governed range;
- inconsistent experiment assignment, exposure or outcome records.

## PostgreSQL controls

`quality.control_results` contains 50 explicit post-load controls covering reference mappings, pricing, acquisition, contracts, subscriptions, billing, payments, usage, customer success, support and experiments. `quality.summary` returns the overall result.

Record-level reconciliation views provide evidence for:

- monthly MRR bridge identity;
- invoice, captured payment and refund amounts;
- overlapping effective-dated subscription items.

## Structural enforcement

The database build applies primary keys, foreign keys and relationship indexes after all typed core tables are loaded. This separates load diagnostics from relationship enforcement while preserving transactional rollback.

## Failure policy

`run-all` stops before report generation when a blocking Python check fails. The PostgreSQL build runs transactionally. On failure, model changes are rolled back and the failure is recorded in `metadata.pipeline_runs` in a new transaction.
