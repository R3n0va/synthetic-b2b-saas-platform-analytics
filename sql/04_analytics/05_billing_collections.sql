CREATE OR REPLACE VIEW analytics.payment_success AS
SELECT
    date_trunc('month', i.invoice_date)::date AS month_start,
    i.region_id,
    i.country_code,
    i.segment,
    pm.method_type,
    count(*) AS invoices,
    count(*) FILTER (WHERE ips.eventually_succeeded) AS successful_invoices,
    count(*) FILTER (WHERE ips.maximum_attempt_number = 1 AND ips.eventually_succeeded) AS first_attempt_successes,
    count(*) FILTER (WHERE ips.eventually_succeeded)::numeric / nullif(count(*), 0) AS eventual_success_rate,
    count(*) FILTER (WHERE ips.maximum_attempt_number = 1 AND ips.eventually_succeeded)::numeric / nullif(count(*), 0) AS first_attempt_success_rate
FROM mart.invoice_payment_summary ips
JOIN core.v_invoices_enriched i USING (invoice_id)
LEFT JOIN core.payment_attempts pa
    ON pa.invoice_id = i.invoice_id AND pa.attempt_number = 1
LEFT JOIN core.payment_methods pm USING (payment_method_id)
GROUP BY 1,2,3,4,5;

CREATE OR REPLACE VIEW analytics.payment_recovery AS
SELECT
    date_trunc('month', invoice_date)::date AS month_start,
    region_id,
    country_code,
    segment,
    count(*) FILTER (WHERE any_failure) AS failed_first_or_later_invoices,
    count(*) FILTER (WHERE any_failure AND eventually_succeeded) AS recovered_invoices,
    sum(total_eur) FILTER (WHERE any_failure) AS failed_value_eur,
    sum(total_eur) FILTER (WHERE any_failure AND eventually_succeeded) AS recovered_value_eur,
    count(*) FILTER (WHERE any_failure AND eventually_succeeded)::numeric /
        nullif(count(*) FILTER (WHERE any_failure), 0) AS recovery_rate
FROM mart.invoice_payment_summary
GROUP BY 1,2,3,4;

CREATE OR REPLACE VIEW analytics.dunning_effectiveness AS
SELECT
    date_trunc('month', d.event_at)::date AS month_start,
    d.dunning_step,
    d.channel,
    count(*) AS dunning_events,
    count(*) FILTER (WHERE d.recovered_after_event_flag) AS recovered_after_event,
    count(*) FILTER (WHERE d.recovered_after_event_flag)::numeric / nullif(count(*), 0) AS recovery_rate
FROM core.dunning_events d
GROUP BY 1,2,3;

CREATE OR REPLACE VIEW analytics.overdue_receivables AS
SELECT
    date_trunc('month', i.due_date)::date AS due_month,
    i.region_id,
    i.country_code,
    i.segment,
    count(*) FILTER (WHERE i.invoice_status IN ('overdue', 'open')) AS unpaid_invoices,
    sum(i.total_eur) FILTER (WHERE i.invoice_status IN ('overdue', 'open')) AS unpaid_eur,
    avg(current_date - i.due_date) FILTER (WHERE i.invoice_status = 'overdue') AS average_days_overdue
FROM core.v_invoices_enriched i
GROUP BY 1,2,3,4;

CREATE OR REPLACE VIEW analytics.refunds_and_credits AS
SELECT
    date_trunc('month', i.invoice_date)::date AS month_start,
    i.region_id,
    i.country_code,
    i.segment,
    sum(i.total_eur) AS invoiced_eur,
    coalesce(sum(c.amount_eur), 0) AS credit_eur,
    coalesce(sum(r.amount_eur), 0) AS refund_eur,
    (coalesce(sum(c.amount_eur), 0) + coalesce(sum(r.amount_eur), 0)) / nullif(sum(i.total_eur), 0) AS adjustment_rate
FROM core.v_invoices_enriched i
LEFT JOIN core.credit_notes c USING (invoice_id)
LEFT JOIN core.payments p USING (invoice_id)
LEFT JOIN core.refunds r USING (payment_id)
GROUP BY 1,2,3,4;

CREATE OR REPLACE VIEW analytics.invoice_reconciliation AS
SELECT
    i.invoice_id,
    i.subtotal_local,
    sum(il.line_total_local) AS invoice_line_total_local,
    i.subtotal_local - sum(il.line_total_local) AS difference_local,
    abs(i.subtotal_local - sum(il.line_total_local)) <= 0.02 AS reconciled
FROM core.invoices i
JOIN core.invoice_lines il USING (invoice_id)
GROUP BY 1,2;
