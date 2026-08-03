CREATE OR REPLACE VIEW mart.invoice_payment_summary AS
SELECT
    i.invoice_id,
    i.account_id,
    i.subscription_id,
    i.invoice_date,
    i.due_date,
    i.country_code,
    i.region_id,
    i.segment,
    i.total_eur,
    i.invoice_status,
    count(pa.payment_attempt_id) AS attempt_count,
    min(pa.attempt_at) AS first_attempt_at,
    min(pa.attempt_at) FILTER (WHERE pa.attempt_status = 'succeeded') AS successful_attempt_at,
    bool_or(pa.attempt_status = 'failed') AS any_failure,
    bool_or(pa.attempt_status = 'succeeded') AS eventually_succeeded,
    max(pa.attempt_number) AS maximum_attempt_number
FROM core.v_invoices_enriched i
LEFT JOIN core.payment_attempts pa USING (invoice_id)
GROUP BY 1,2,3,4,5,6,7,8,9,10;

CREATE OR REPLACE VIEW mart.sales_funnel_account AS
SELECT
    a.account_id,
    a.country_code,
    a.region_id,
    a.segment,
    a.sales_motion,
    a.acquisition_channel,
    l.lead_id,
    (l.mql_at IS NOT NULL) AS reached_mql,
    (l.sql_at IS NOT NULL) AS reached_sql,
    o.opportunity_id,
    o.status AS opportunity_status,
    o.expected_arr_eur,
    s.subscription_id,
    s.subscription_start_date,
    (s.subscription_id IS NOT NULL) AS became_customer
FROM core.accounts a
LEFT JOIN core.leads l USING (account_id)
LEFT JOIN core.opportunities o USING (account_id)
LEFT JOIN core.subscriptions s USING (account_id);

CREATE OR REPLACE VIEW mart.experiment_analysis AS
SELECT
    e.experiment_id,
    e.experiment_name,
    a.variant,
    count(DISTINCT a.assignment_id) AS assigned_accounts,
    count(DISTINCT x.assignment_id) AS exposed_accounts,
    avg(o.primary_outcome) AS primary_mean,
    avg(o.guardrail_outcome) AS guardrail_mean,
    avg(o.revenue_outcome_eur) AS average_revenue_outcome_eur
FROM core.experiments e
JOIN core.experiment_assignments a USING (experiment_id)
LEFT JOIN core.experiment_exposures x USING (assignment_id)
LEFT JOIN core.experiment_outcomes o USING (assignment_id)
GROUP BY 1,2,3;
