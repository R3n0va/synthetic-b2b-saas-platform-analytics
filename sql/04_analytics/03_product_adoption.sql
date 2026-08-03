CREATE OR REPLACE VIEW analytics.product_adoption AS
SELECT
    month_start,
    region_id,
    country_code,
    segment,
    count(*) FILTER (WHERE mrr_eur > 0) AS paid_accounts,
    count(*) FILTER (WHERE active_users > 0) AS active_accounts,
    sum(active_users) AS active_users,
    sum(sessions) AS sessions,
    avg(feature_breadth) FILTER (WHERE active_users > 0) AS average_feature_breadth,
    count(*) FILTER (WHERE automation_runs > 0)::numeric / nullif(count(*) FILTER (WHERE mrr_eur > 0), 0) AS automation_adoption_rate,
    count(*) FILTER (WHERE api_calls > 0)::numeric / nullif(count(*) FILTER (WHERE mrr_eur > 0), 0) AS api_adoption_rate
FROM mart.account_month
GROUP BY 1,2,3,4;

CREATE OR REPLACE VIEW analytics.seat_utilisation AS
SELECT
    month_start,
    region_id,
    country_code,
    segment,
    primary_plan_name,
    sum(active_users) AS active_users,
    sum(paid_seats) AS paid_seats,
    sum(active_users)::numeric / nullif(sum(paid_seats), 0) AS seat_utilisation,
    count(*) FILTER (WHERE paid_seats > 0 AND active_users::numeric / paid_seats < 0.40) AS underutilised_accounts
FROM mart.account_month
GROUP BY 1,2,3,4,5;

CREATE OR REPLACE VIEW analytics.workflow_completion AS
SELECT
    month_start,
    region_id,
    country_code,
    segment,
    sum(work_orders_created) AS work_orders_created,
    sum(work_orders_completed) AS work_orders_completed,
    sum(work_orders_completed)::numeric / nullif(sum(work_orders_created), 0) AS completion_rate,
    sum(work_orders_created)::numeric / nullif(count(*) FILTER (WHERE mrr_eur > 0), 0) AS work_orders_per_paid_account
FROM mart.account_month
GROUP BY 1,2,3,4;

CREATE OR REPLACE VIEW analytics.onboarding_completion AS
SELECT
    a.country_code,
    a.region_id,
    a.segment,
    a.sales_motion,
    count(DISTINCT o.account_id) AS onboarding_accounts,
    count(*) AS onboarding_tasks,
    count(*) FILTER (WHERE o.task_status = 'completed') AS completed_tasks,
    count(*) FILTER (WHERE o.task_status = 'completed')::numeric / nullif(count(*), 0) AS task_completion_rate,
    avg(o.completed_at::date - s.subscription_start_date) FILTER (WHERE o.completed_at IS NOT NULL) AS average_days_to_task
FROM core.onboarding_tasks o
JOIN core.accounts a USING (account_id)
JOIN core.subscriptions s USING (account_id)
GROUP BY 1,2,3,4;

CREATE OR REPLACE VIEW analytics.time_to_first_value AS
SELECT
    a.country_code,
    a.region_id,
    a.segment,
    a.sales_motion,
    avg(first_work_order.first_completed_at::date - s.subscription_start_date) AS average_days_to_first_completed_work_order,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY first_work_order.first_completed_at::date - s.subscription_start_date) AS median_days_to_first_value
FROM core.subscriptions s
JOIN core.accounts a USING (account_id)
JOIN (
    SELECT account_id, min(completed_at) AS first_completed_at
    FROM core.work_orders
    WHERE status = 'completed'
    GROUP BY account_id
) first_work_order USING (account_id)
GROUP BY 1,2,3,4;

CREATE OR REPLACE VIEW analytics.integration_adoption AS
SELECT
    a.region_id,
    a.country_code,
    a.segment,
    i.integration_type,
    count(DISTINCT i.account_id) AS connected_accounts,
    avg(i.monthly_sync_volume) AS average_monthly_sync_volume,
    count(*) FILTER (WHERE i.integration_status = 'active')::numeric / nullif(count(*), 0) AS active_integration_rate
FROM core.integrations i
JOIN core.accounts a USING (account_id)
GROUP BY 1,2,3,4;

CREATE OR REPLACE VIEW analytics.usage_before_churn AS
SELECT
    am.segment,
    am.primary_plan_name,
    avg(am.active_users) AS average_active_users,
    avg(am.sessions) AS average_sessions,
    avg(am.feature_breadth) AS average_feature_breadth,
    avg(am.work_orders_completed) AS average_completed_work_orders
FROM mart.account_month am
JOIN core.subscriptions s USING (account_id)
WHERE s.ended_date IS NOT NULL
  AND am.month_start BETWEEN date_trunc('month', s.ended_date)::date - interval '2 months'
                         AND date_trunc('month', s.ended_date)::date
GROUP BY 1,2;
