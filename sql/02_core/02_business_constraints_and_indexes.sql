CREATE UNIQUE INDEX IF NOT EXISTS uq_contracts_contract_number
    ON core.contracts (contract_number);

CREATE UNIQUE INDEX IF NOT EXISTS uq_invoices_invoice_number
    ON core.invoices (invoice_number);

CREATE INDEX IF NOT EXISTS idx_accounts_country_segment
    ON core.accounts (country_code, segment);

CREATE INDEX IF NOT EXISTS idx_accounts_sales_motion
    ON core.accounts (sales_motion, acquisition_channel);

CREATE INDEX IF NOT EXISTS idx_subscriptions_status_start
    ON core.subscriptions (current_status, subscription_start_date);

CREATE INDEX IF NOT EXISTS idx_subscription_items_effective_dates
    ON core.subscription_items (subscription_id, effective_start, effective_end);

CREATE INDEX IF NOT EXISTS idx_subscription_events_event_at
    ON core.subscription_events (subscription_id, event_at);

CREATE INDEX IF NOT EXISTS idx_invoices_account_date
    ON core.invoices (account_id, invoice_date);

CREATE INDEX IF NOT EXISTS idx_payment_attempts_invoice_attempt
    ON core.payment_attempts (invoice_id, attempt_number);

CREATE INDEX IF NOT EXISTS idx_usage_account_date
    ON core.account_usage_daily (account_id, activity_date);

CREATE INDEX IF NOT EXISTS idx_product_events_account_date
    ON core.product_events (account_id, event_at);

CREATE INDEX IF NOT EXISTS idx_support_account_created
    ON core.support_tickets (account_id, created_at);

CREATE INDEX IF NOT EXISTS idx_health_account_month
    ON core.account_health_history (account_id, health_month);

CREATE INDEX IF NOT EXISTS idx_renewals_due_status
    ON core.renewals (renewal_due_date, renewal_status);
