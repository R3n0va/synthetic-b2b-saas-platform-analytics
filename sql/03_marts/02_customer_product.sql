CREATE OR REPLACE VIEW mart.account_usage_monthly AS
SELECT
    date_trunc('month', activity_date)::date AS month_start,
    account_id,
    max(active_users) AS active_users,
    max(active_mobile_users) AS active_mobile_users,
    sum(sessions) AS sessions,
    sum(work_orders_created) AS work_orders_created,
    sum(work_orders_completed) AS work_orders_completed,
    sum(automation_runs) AS automation_runs,
    sum(api_calls) AS api_calls,
    sum(documents_uploaded) AS documents_uploaded,
    max(feature_breadth) AS feature_breadth
FROM core.account_usage_daily
GROUP BY 1, 2;

CREATE OR REPLACE VIEW mart.support_monthly AS
SELECT
    date_trunc('month', created_at)::date AS month_start,
    account_id,
    count(*) AS tickets,
    count(*) FILTER (WHERE escalated_flag) AS escalated_tickets,
    avg(extract(epoch FROM (first_response_at - created_at)) / 3600.0) AS avg_first_response_hours,
    avg(extract(epoch FROM (resolved_at - created_at)) / 3600.0) AS avg_resolution_hours,
    avg(csat_score) AS avg_csat,
    sum(reopened_count) AS reopened_count
FROM core.support_tickets
GROUP BY 1, 2;

CREATE OR REPLACE VIEW mart.payment_monthly AS
SELECT
    date_trunc('month', i.invoice_date)::date AS month_start,
    i.account_id,
    count(*) AS invoices,
    count(*) FILTER (WHERE i.invoice_status = 'paid') AS paid_invoices,
    count(*) FILTER (WHERE i.invoice_status IN ('overdue', 'open')) AS unpaid_invoices,
    sum(i.total_eur) AS invoiced_eur,
    sum(i.total_eur) FILTER (WHERE i.invoice_status = 'paid') AS paid_eur
FROM core.invoices i
GROUP BY 1, 2;

CREATE OR REPLACE VIEW mart.account_month AS
SELECT
    m.month_start,
    m.account_id,
    a.country_code,
    a.region_id,
    a.segment,
    a.sales_motion,
    a.acquisition_channel,
    m.mrr_eur,
    m.paid_seats,
    m.active_add_ons,
    m.primary_plan_name,
    coalesce(u.active_users, 0) AS active_users,
    coalesce(u.sessions, 0) AS sessions,
    coalesce(u.work_orders_created, 0) AS work_orders_created,
    coalesce(u.work_orders_completed, 0) AS work_orders_completed,
    coalesce(u.automation_runs, 0) AS automation_runs,
    coalesce(u.api_calls, 0) AS api_calls,
    coalesce(u.feature_breadth, 0) AS feature_breadth,
    coalesce(s.tickets, 0) AS support_tickets,
    coalesce(s.escalated_tickets, 0) AS escalated_tickets,
    coalesce(p.unpaid_invoices, 0) AS unpaid_invoices,
    h.health_score,
    h.health_segment,
    h.renewal_risk_flag
FROM mart.account_mrr_complete m
JOIN core.accounts a USING (account_id)
LEFT JOIN mart.account_usage_monthly u USING (month_start, account_id)
LEFT JOIN mart.support_monthly s USING (month_start, account_id)
LEFT JOIN mart.payment_monthly p USING (month_start, account_id)
LEFT JOIN core.account_health_history h
    ON h.account_id = m.account_id AND h.health_month = m.month_start;
