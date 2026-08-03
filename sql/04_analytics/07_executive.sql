CREATE OR REPLACE VIEW analytics.executive_monthly_scorecard AS
SELECT
    b.month_start,
    b.closing_mrr,
    b.closing_arr,
    b.new_mrr,
    b.expansion_mrr,
    b.contraction_mrr,
    b.churned_mrr,
    b.reactivation_mrr,
    rr.gross_revenue_retention,
    rr.net_revenue_retention,
    lc.opening_accounts,
    lc.churned_accounts,
    lc.logo_churn_rate,
    sum(am.paid_seats) AS paid_seats,
    sum(am.active_users) AS active_users,
    sum(am.active_users)::numeric / nullif(sum(am.paid_seats), 0) AS seat_utilisation,
    count(*) FILTER (WHERE am.renewal_risk_flag) AS risk_accounts,
    sum(am.mrr_eur) FILTER (WHERE am.renewal_risk_flag) AS risk_mrr_eur
FROM analytics.monthly_mrr_bridge b
LEFT JOIN analytics.revenue_retention rr USING (month_start)
LEFT JOIN analytics.logo_churn lc USING (month_start)
LEFT JOIN mart.account_month am USING (month_start)
GROUP BY 1,2,3,4,5,6,7,8,9,10,11,12,13;

CREATE OR REPLACE VIEW analytics.latest_executive_scorecard AS
SELECT *
FROM analytics.executive_monthly_scorecard
ORDER BY month_start DESC
LIMIT 1;

CREATE OR REPLACE VIEW analytics.regional_operating_review AS
SELECT
    am.month_start,
    am.region_id,
    sum(am.mrr_eur) AS mrr_eur,
    count(*) FILTER (WHERE am.mrr_eur > 0) AS active_accounts,
    sum(am.paid_seats) AS paid_seats,
    sum(am.active_users) AS active_users,
    sum(am.work_orders_completed) AS completed_work_orders,
    sum(am.support_tickets) AS support_tickets,
    count(*) FILTER (WHERE am.renewal_risk_flag) AS renewal_risk_accounts,
    avg(am.health_score) AS average_health_score
FROM mart.account_month am
GROUP BY 1,2;
