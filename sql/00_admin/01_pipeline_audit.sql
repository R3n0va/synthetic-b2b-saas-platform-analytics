CREATE OR REPLACE VIEW metadata.latest_pipeline_run AS
SELECT *
FROM metadata.pipeline_runs
ORDER BY pipeline_run_id DESC
LIMIT 1;

CREATE OR REPLACE VIEW metadata.source_row_counts AS
SELECT 'accounts' AS table_name, count(*)::bigint AS row_count FROM core.accounts
UNION ALL SELECT 'subscriptions', count(*) FROM core.subscriptions
UNION ALL SELECT 'subscription_items', count(*) FROM core.subscription_items
UNION ALL SELECT 'invoices', count(*) FROM core.invoices
UNION ALL SELECT 'payment_attempts', count(*) FROM core.payment_attempts
UNION ALL SELECT 'account_usage_daily', count(*) FROM core.account_usage_daily
UNION ALL SELECT 'product_events', count(*) FROM core.product_events
UNION ALL SELECT 'support_tickets', count(*) FROM core.support_tickets
UNION ALL SELECT 'experiment_assignments', count(*) FROM core.experiment_assignments;
