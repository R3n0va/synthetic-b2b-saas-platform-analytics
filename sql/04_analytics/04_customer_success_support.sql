CREATE OR REPLACE VIEW analytics.account_health_distribution AS
SELECT
    health_month,
    a.region_id,
    a.country_code,
    a.segment,
    h.health_segment,
    count(*) AS accounts,
    avg(h.health_score) AS average_health_score,
    sum(am.mrr_eur) AS mrr_eur
FROM core.account_health_history h
JOIN core.accounts a USING (account_id)
LEFT JOIN mart.account_month am
    ON am.account_id = h.account_id AND am.month_start = h.health_month
GROUP BY 1,2,3,4,5;

CREATE OR REPLACE VIEW analytics.renewal_risk AS
SELECT
    am.month_start,
    am.region_id,
    am.country_code,
    am.segment,
    count(*) FILTER (WHERE am.renewal_risk_flag) AS risk_accounts,
    sum(am.mrr_eur) FILTER (WHERE am.renewal_risk_flag) AS risk_mrr_eur,
    avg(am.health_score) FILTER (WHERE am.renewal_risk_flag) AS average_risk_health_score,
    count(*) FILTER (WHERE am.unpaid_invoices > 0) AS payment_risk_accounts,
    count(*) FILTER (WHERE am.support_tickets >= 2) AS support_risk_accounts
FROM mart.account_month am
GROUP BY 1,2,3,4;

CREATE OR REPLACE VIEW analytics.renewal_pipeline AS
SELECT
    date_trunc('month', r.renewal_due_date)::date AS renewal_month,
    a.region_id,
    a.country_code,
    a.segment,
    r.renewal_status,
    count(*) AS renewals,
    sum(r.renewal_arr_eur) AS renewal_arr_eur,
    avg(r.renewal_probability) AS average_renewal_probability,
    sum(r.renewal_arr_eur * r.renewal_probability) AS probability_weighted_arr
FROM core.renewals r
JOIN core.subscriptions s USING (subscription_id)
JOIN core.accounts a USING (account_id)
GROUP BY 1,2,3,4,5;

CREATE OR REPLACE VIEW analytics.customer_success_intervention AS
SELECT
    date_trunc('month', c.interaction_at)::date AS month_start,
    a.region_id,
    a.segment,
    c.interaction_type,
    c.reason,
    count(*) AS interactions,
    avg(c.health_score_before) AS average_health_before,
    avg(c.health_score_after) AS average_health_after,
    avg(c.health_score_after - c.health_score_before) AS average_health_lift
FROM core.customer_success_interactions c
JOIN core.accounts a USING (account_id)
GROUP BY 1,2,3,4,5;

CREATE OR REPLACE VIEW analytics.support_service_levels AS
SELECT
    date_trunc('month', t.created_at)::date AS month_start,
    a.region_id,
    a.country_code,
    a.segment,
    t.priority,
    t.category,
    count(*) AS tickets,
    avg(extract(epoch FROM (t.first_response_at - t.created_at)) / 3600.0) AS average_first_response_hours,
    avg(extract(epoch FROM (t.resolved_at - t.created_at)) / 3600.0) AS average_resolution_hours,
    count(*) FILTER (WHERE t.escalated_flag)::numeric / nullif(count(*), 0) AS escalation_rate,
    avg(t.csat_score) AS average_csat
FROM core.support_tickets t
JOIN core.accounts a USING (account_id)
GROUP BY 1,2,3,4,5,6;

CREATE OR REPLACE VIEW analytics.nps AS
SELECT
    date_trunc('month', n.response_date)::date AS month_start,
    a.region_id,
    a.country_code,
    a.segment,
    count(*) AS responses,
    avg(n.nps_score) AS average_score,
    100.0 * (
        count(*) FILTER (WHERE n.nps_group = 'promoter')::numeric / nullif(count(*), 0)
        - count(*) FILTER (WHERE n.nps_group = 'detractor')::numeric / nullif(count(*), 0)
    ) AS nps,
    mode() WITHIN GROUP (ORDER BY n.comment_theme) AS leading_comment_theme
FROM core.nps_responses n
JOIN core.accounts a USING (account_id)
GROUP BY 1,2,3,4;

CREATE OR REPLACE VIEW analytics.churn_reasons AS
SELECT
    date_trunc('month', se.event_at)::date AS churn_month,
    a.region_id,
    a.country_code,
    a.segment,
    s.churn_type,
    coalesce(cancel.event_reason, se.event_reason) AS churn_reason,
    count(*) AS churned_accounts,
    -sum(se.mrr_change_eur) AS churned_mrr_eur
FROM core.subscription_events se
JOIN core.subscriptions s USING (subscription_id)
JOIN core.accounts a USING (account_id)
LEFT JOIN LATERAL (
    SELECT event_reason
    FROM core.subscription_events x
    WHERE x.subscription_id = se.subscription_id
      AND x.event_type = 'cancellation_requested'
    ORDER BY event_at DESC
    LIMIT 1
) cancel ON true
WHERE se.event_type = 'subscription_churned'
GROUP BY 1,2,3,4,5,6;
