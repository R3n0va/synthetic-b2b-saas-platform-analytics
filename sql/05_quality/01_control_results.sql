CREATE OR REPLACE VIEW quality.control_results AS
SELECT 'Q001'::text AS control_id, 'subscriptions'::text AS table_name,
       'subscription_start_before_end'::text AS control_name,
       count(*) FILTER (WHERE ended_date IS NOT NULL AND ended_date < subscription_start_date)::bigint AS failure_count,
       'error'::text AS severity
FROM core.subscriptions
UNION ALL
SELECT 'Q002', 'subscription_items', 'effective_interval_valid',
       count(*) FILTER (WHERE effective_end < effective_start), 'error'
FROM core.subscription_items
UNION ALL
SELECT 'Q003', 'subscription_items', 'non_negative_mrr',
       count(*) FILTER (WHERE mrr_eur < 0 OR mrr_local < 0), 'error'
FROM core.subscription_items
UNION ALL
SELECT 'Q004', 'invoices', 'invoice_arithmetic',
       count(*) FILTER (WHERE abs(subtotal_local + tax_local - total_local) > 0.02), 'error'
FROM core.invoices
UNION ALL
SELECT 'Q005', 'invoice_lines', 'invoice_line_reconciliation',
       count(*) FILTER (WHERE NOT reconciled), 'error'
FROM analytics.invoice_reconciliation
UNION ALL
SELECT 'Q006', 'payments', 'payment_references_successful_attempt',
       count(*) FILTER (WHERE pa.attempt_status <> 'succeeded'), 'error'
FROM core.payments p
JOIN core.payment_attempts pa USING (payment_attempt_id)
UNION ALL
SELECT 'Q007', 'payment_attempts', 'attempt_numbers_and_amounts_positive',
       count(*) FILTER (WHERE attempt_number < 1 OR amount_local <= 0), 'error'
FROM core.payment_attempts
UNION ALL
SELECT 'Q008', 'account_usage_daily', 'usage_counts_non_negative',
       count(*) FILTER (WHERE active_users < 0 OR active_mobile_users < 0 OR sessions < 0
                         OR work_orders_created < 0 OR work_orders_completed < 0
                         OR automation_runs < 0 OR api_calls < 0 OR documents_uploaded < 0), 'error'
FROM core.account_usage_daily
UNION ALL
SELECT 'Q009', 'work_orders', 'work_order_chronology',
       count(*) FILTER (WHERE completed_at IS NOT NULL AND completed_at < created_at), 'error'
FROM core.work_orders
UNION ALL
SELECT 'Q010', 'support_tickets', 'ticket_chronology',
       count(*) FILTER (WHERE first_response_at < created_at OR resolved_at < created_at
                         OR closed_at < resolved_at), 'error'
FROM core.support_tickets
UNION ALL
SELECT 'Q011', 'account_health_history', 'health_score_range',
       count(*) FILTER (WHERE health_score < 0 OR health_score > 100), 'error'
FROM core.account_health_history
UNION ALL
SELECT 'Q012', 'nps_responses', 'nps_score_range',
       count(*) FILTER (WHERE nps_score < 0 OR nps_score > 10), 'error'
FROM core.nps_responses
UNION ALL
SELECT 'Q013', 'mrr_movements', 'mrr_bridge_reconciliation',
       count(*) FILTER (WHERE abs(closing_mrr - (opening_mrr + coalesce(new_mrr, 0)
                         + coalesce(expansion_mrr, 0) + coalesce(contraction_mrr, 0)
                         + coalesce(churned_mrr, 0) + coalesce(reactivation_mrr, 0))) > 0.02), 'error'
FROM analytics.monthly_mrr_bridge
UNION ALL
SELECT 'Q014', 'experiment_assignments', 'one_assignment_per_account_experiment',
       count(*), 'error'
FROM (
    SELECT experiment_id, account_id
    FROM core.experiment_assignments
    GROUP BY 1, 2
    HAVING count(*) > 1
) d
UNION ALL
SELECT 'Q015', 'contracts', 'contract_date_order',
       count(*) FILTER (WHERE end_date < start_date OR signed_date > start_date), 'error'
FROM core.contracts
UNION ALL
SELECT 'Q016', 'renewals', 'renewal_decision_before_due',
       count(*) FILTER (WHERE decision_date IS NOT NULL AND decision_date > renewal_due_date), 'warning'
FROM core.renewals
UNION ALL
SELECT 'Q017', 'accounts', 'country_mapping_complete',
       count(*) FILTER (WHERE c.country_code IS NULL), 'error'
FROM core.accounts a
LEFT JOIN core.countries c USING (country_code)
UNION ALL
SELECT 'Q018', 'subscription_events', 'churn_event_negative_mrr',
       count(*) FILTER (WHERE event_type = 'subscription_churned' AND mrr_change_eur >= 0), 'error'
FROM core.subscription_events
UNION ALL
SELECT 'Q019', 'subscriptions', 'churn_status_consistent',
       count(*) FILTER (WHERE (current_status = 'churned') <> (ended_date IS NOT NULL)), 'error'
FROM core.subscriptions
UNION ALL
SELECT 'Q020', 'invoices', 'paid_invoice_has_paid_date',
       count(*) FILTER (WHERE invoice_status = 'paid' AND paid_date IS NULL), 'error'
FROM core.invoices
UNION ALL
SELECT 'Q021', 'countries', 'region_mapping_complete',
       count(*) FILTER (WHERE r.region_id IS NULL), 'error'
FROM core.countries c
LEFT JOIN core.regions r USING (region_id)
UNION ALL
SELECT 'Q022', 'countries', 'vat_rate_range',
       count(*) FILTER (WHERE vat_rate < 0 OR vat_rate > 0.30), 'error'
FROM core.countries
UNION ALL
SELECT 'Q023', 'fx_rates', 'positive_eur_rate',
       count(*) FILTER (WHERE eur_rate <= 0), 'error'
FROM core.fx_rates
UNION ALL
SELECT 'Q024', 'plan_prices', 'price_and_effective_date_validity',
       count(*) FILTER (WHERE effective_end < effective_start OR base_price < 0 OR seat_price < 0
                         OR annual_discount_pct < 0 OR annual_discount_pct >= 1), 'error'
FROM core.plan_prices
UNION ALL
SELECT 'Q025', 'accounts', 'account_region_matches_country',
       count(*) FILTER (WHERE a.region_id <> c.region_id), 'error'
FROM core.accounts a
JOIN core.countries c USING (country_code)
UNION ALL
SELECT 'Q026', 'accounts', 'partner_led_accounts_have_partner',
       count(*) FILTER (WHERE sales_motion = 'partner_led' AND partner_id IS NULL), 'error'
FROM core.accounts
UNION ALL
SELECT 'Q027', 'leads', 'lead_lifecycle_order',
       count(*) FILTER (WHERE mql_at < created_at OR sql_at < coalesce(mql_at, created_at)), 'error'
FROM core.leads
UNION ALL
SELECT 'Q028', 'leads', 'lead_score_range',
       count(*) FILTER (WHERE lead_score < 0 OR lead_score > 100), 'error'
FROM core.leads
UNION ALL
SELECT 'Q029', 'opportunities', 'opportunity_date_order',
       count(*) FILTER (WHERE close_date < created_at), 'error'
FROM core.opportunities
UNION ALL
SELECT 'Q030', 'opportunities', 'opportunity_probability_range',
       count(*) FILTER (WHERE probability < 0 OR probability > 1), 'error'
FROM core.opportunities
UNION ALL
SELECT 'Q031', 'opportunity_stage_history', 'stage_history_date_order',
       count(*) FILTER (WHERE exited_at IS NOT NULL AND exited_at < entered_at), 'error'
FROM core.opportunity_stage_history
UNION ALL
SELECT 'Q032', 'users', 'user_lifecycle_order',
       count(*) FILTER (WHERE invited_at < created_at OR activated_at < invited_at
                         OR deactivated_at < activated_at), 'error'
FROM core.users
UNION ALL
SELECT 'Q033', 'subscriptions', 'trial_and_subscription_date_order',
       count(*) FILTER (WHERE trial_end_date < trial_start_date
                         OR subscription_start_date < trial_start_date), 'error'
FROM core.subscriptions
UNION ALL
SELECT 'Q034', 'subscription_items', 'item_type_reference_exclusive',
       count(*) FILTER (WHERE (item_type = 'plan' AND (plan_id IS NULL OR add_on_id IS NOT NULL))
                         OR (item_type = 'add_on' AND (add_on_id IS NULL OR plan_id IS NOT NULL))), 'error'
FROM core.subscription_items
UNION ALL
SELECT 'Q035', 'subscription_items', 'positive_item_quantity',
       count(*) FILTER (WHERE quantity <= 0), 'error'
FROM core.subscription_items
UNION ALL
SELECT 'Q036', 'renewals', 'renewal_probability_range',
       count(*) FILTER (WHERE renewal_probability < 0 OR renewal_probability > 1), 'error'
FROM core.renewals
UNION ALL
SELECT 'Q037', 'invoices', 'invoice_date_order',
       count(*) FILTER (WHERE due_date < invoice_date OR service_period_end < service_period_start), 'error'
FROM core.invoices
UNION ALL
SELECT 'Q038', 'invoices', 'invoice_amounts_non_negative',
       count(*) FILTER (WHERE subtotal_local < 0 OR tax_local < 0 OR total_local < 0 OR total_eur < 0), 'error'
FROM core.invoices
UNION ALL
SELECT 'Q039', 'invoice_lines', 'invoice_line_arithmetic',
       count(*) FILTER (WHERE abs(quantity * unit_price_local - discount_local - line_total_local) > 0.02), 'error'
FROM core.invoice_lines
UNION ALL
SELECT 'Q040', 'payments', 'captured_payment_amounts_positive',
       count(*) FILTER (WHERE amount_local <= 0 OR amount_eur <= 0), 'error'
FROM core.payments
UNION ALL
SELECT 'Q041', 'refunds', 'refund_date_and_amount_validity',
       count(*) FILTER (WHERE processed_at < requested_at OR amount_local <= 0 OR amount_eur <= 0), 'error'
FROM core.refunds
UNION ALL
SELECT 'Q042', 'refunds', 'refund_does_not_exceed_payment',
       count(*) FILTER (WHERE r.amount_local > p.amount_local + 0.02), 'error'
FROM core.refunds r
JOIN core.payments p USING (payment_id)
UNION ALL
SELECT 'Q043', 'credit_notes', 'credit_note_does_not_exceed_invoice',
       count(*) FILTER (WHERE c.amount_local <= 0 OR c.amount_local > i.total_local + 0.02), 'error'
FROM core.credit_notes c
JOIN core.invoices i USING (invoice_id)
UNION ALL
SELECT 'Q044', 'dunning_events', 'dunning_not_before_invoice',
       count(*) FILTER (WHERE d.event_at::date < i.invoice_date), 'error'
FROM core.dunning_events d
JOIN core.invoices i USING (invoice_id)
UNION ALL
SELECT 'Q045', 'product_events', 'event_account_matches_user',
       count(*) FILTER (WHERE e.account_id <> u.account_id), 'error'
FROM core.product_events e
JOIN core.users u USING (user_id)
UNION ALL
SELECT 'Q046', 'integrations', 'integration_date_order',
       count(*) FILTER (WHERE disconnected_at IS NOT NULL AND disconnected_at < connected_at), 'error'
FROM core.integrations
UNION ALL
SELECT 'Q047', 'work_orders', 'scheduled_and_completed_date_order',
       count(*) FILTER (WHERE scheduled_at < created_at OR completed_at < scheduled_at), 'error'
FROM core.work_orders
UNION ALL
SELECT 'Q048', 'onboarding_tasks', 'completed_task_has_completion_date',
       count(*) FILTER (WHERE task_status = 'completed' AND completed_at IS NULL), 'error'
FROM core.onboarding_tasks
UNION ALL
SELECT 'Q049', 'customer_success_interactions', 'health_score_components_range',
       count(*) FILTER (WHERE health_score_before < 0 OR health_score_before > 100
                         OR health_score_after < 0 OR health_score_after > 100), 'error'
FROM core.customer_success_interactions
UNION ALL
SELECT 'Q050', 'support_tickets', 'csat_score_range',
       count(*) FILTER (WHERE csat_score IS NOT NULL AND (csat_score < 1 OR csat_score > 5)), 'error'
FROM core.support_tickets;

CREATE OR REPLACE VIEW quality.summary AS
SELECT
    count(*) AS controls,
    count(*) FILTER (WHERE failure_count = 0) AS passed_controls,
    count(*) FILTER (WHERE failure_count > 0) AS failed_controls,
    sum(failure_count) AS total_failures,
    CASE
        WHEN count(*) FILTER (WHERE failure_count > 0 AND severity = 'error') = 0 THEN 'PASS'
        ELSE 'FAIL'
    END AS quality_status
FROM quality.control_results;
