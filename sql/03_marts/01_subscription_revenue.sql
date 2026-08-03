CREATE OR REPLACE VIEW mart.subscription_item_monthly AS
SELECT
    gs.month_start::date AS month_start,
    si.subscription_item_id,
    si.subscription_id,
    si.account_id,
    si.item_type,
    si.plan_id,
    si.plan_name,
    si.add_on_id,
    si.add_on_name,
    si.quantity,
    si.mrr_local,
    si.mrr_eur
FROM core.v_subscription_items_enriched si
CROSS JOIN LATERAL generate_series(
    date_trunc('month', si.effective_start)::date,
    date_trunc('month', si.effective_end)::date,
    interval '1 month'
) AS gs(month_start);

CREATE OR REPLACE VIEW mart.subscription_monthly AS
SELECT
    sim.month_start,
    sim.subscription_id,
    sim.account_id,
    max(CASE WHEN sim.item_type = 'plan' THEN sim.plan_id END) AS plan_id,
    max(CASE WHEN sim.item_type = 'plan' THEN sim.plan_name END) AS plan_name,
    max(CASE WHEN sim.item_type = 'plan' THEN sim.quantity END) AS paid_seats,
    count(*) FILTER (WHERE sim.item_type = 'add_on') AS active_add_ons,
    sum(sim.mrr_local) AS mrr_local,
    sum(sim.mrr_eur) AS mrr_eur
FROM mart.subscription_item_monthly sim
GROUP BY 1, 2, 3;

CREATE OR REPLACE VIEW mart.account_mrr_monthly AS
SELECT
    sm.month_start,
    sm.account_id,
    sum(sm.mrr_eur) AS mrr_eur,
    sum(sm.mrr_local) AS mrr_local,
    max(sm.paid_seats) AS paid_seats,
    sum(sm.active_add_ons) AS active_add_ons,
    max(sm.plan_name) AS primary_plan_name
FROM mart.subscription_monthly sm
GROUP BY 1, 2;

CREATE OR REPLACE VIEW mart.account_mrr_complete AS
WITH bounds AS (
    SELECT min(month_start) AS min_month, max(month_start) AS max_month
    FROM mart.account_mrr_monthly
),
months AS (
    SELECT generate_series(min_month, max_month, interval '1 month')::date AS month_start
    FROM bounds
),
accounts AS (
    SELECT DISTINCT account_id FROM mart.account_mrr_monthly
)
SELECT
    m.month_start,
    a.account_id,
    coalesce(am.mrr_eur, 0::numeric) AS mrr_eur,
    coalesce(am.mrr_local, 0::numeric) AS mrr_local,
    coalesce(am.paid_seats, 0) AS paid_seats,
    coalesce(am.active_add_ons, 0) AS active_add_ons,
    am.primary_plan_name
FROM months m
CROSS JOIN accounts a
LEFT JOIN mart.account_mrr_monthly am USING (month_start, account_id);

CREATE OR REPLACE VIEW mart.mrr_movements AS
WITH staged AS (
    SELECT
        am.*,
        lag(mrr_eur, 1, 0::numeric) OVER (PARTITION BY account_id ORDER BY month_start) AS previous_mrr,
        max(CASE WHEN mrr_eur > 0 THEN 1 ELSE 0 END) OVER (
            PARTITION BY account_id ORDER BY month_start
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        ) AS active_before
    FROM mart.account_mrr_complete am
)
SELECT
    month_start,
    account_id,
    previous_mrr,
    mrr_eur,
    mrr_eur - previous_mrr AS movement_mrr,
    CASE
        WHEN previous_mrr = 0 AND mrr_eur > 0 AND coalesce(active_before, 0) = 0 THEN 'new'
        WHEN previous_mrr = 0 AND mrr_eur > 0 AND active_before = 1 THEN 'reactivation'
        WHEN previous_mrr > 0 AND mrr_eur = 0 THEN 'churn'
        WHEN mrr_eur > previous_mrr AND previous_mrr > 0 THEN 'expansion'
        WHEN mrr_eur < previous_mrr AND mrr_eur > 0 THEN 'contraction'
        ELSE 'no_change'
    END AS movement_type
FROM staged;
