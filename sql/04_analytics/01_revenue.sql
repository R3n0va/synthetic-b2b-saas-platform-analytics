CREATE OR REPLACE VIEW analytics.monthly_mrr_bridge AS
SELECT
    month_start,
    sum(previous_mrr) AS opening_mrr,
    sum(movement_mrr) FILTER (WHERE movement_type = 'new') AS new_mrr,
    sum(movement_mrr) FILTER (WHERE movement_type = 'expansion') AS expansion_mrr,
    sum(movement_mrr) FILTER (WHERE movement_type = 'contraction') AS contraction_mrr,
    sum(movement_mrr) FILTER (WHERE movement_type = 'churn') AS churned_mrr,
    sum(movement_mrr) FILTER (WHERE movement_type = 'reactivation') AS reactivation_mrr,
    sum(mrr_eur) AS closing_mrr,
    sum(mrr_eur) * 12 AS closing_arr
FROM mart.mrr_movements
GROUP BY 1;

CREATE OR REPLACE VIEW analytics.mrr_by_geography AS
SELECT
    month_start,
    region_id,
    country_code,
    sum(mrr_eur) AS mrr_eur,
    sum(mrr_eur) * 12 AS arr_eur,
    count(*) FILTER (WHERE mrr_eur > 0) AS active_accounts,
    avg(mrr_eur) FILTER (WHERE mrr_eur > 0) AS arpa_eur
FROM mart.account_month
GROUP BY 1,2,3;

CREATE OR REPLACE VIEW analytics.mrr_by_segment AS
SELECT
    month_start,
    segment,
    primary_plan_name,
    sum(mrr_eur) AS mrr_eur,
    count(*) FILTER (WHERE mrr_eur > 0) AS active_accounts,
    sum(paid_seats) AS paid_seats,
    sum(mrr_eur) / nullif(sum(paid_seats), 0) AS mrr_per_paid_seat
FROM mart.account_month
GROUP BY 1,2,3;

CREATE OR REPLACE VIEW analytics.revenue_retention AS
WITH movement AS (
    SELECT
        month_start,
        sum(previous_mrr) AS opening_mrr,
        -sum(movement_mrr) FILTER (WHERE movement_type IN ('churn', 'contraction')) AS lost_mrr,
        sum(movement_mrr) FILTER (WHERE movement_type = 'expansion') AS expansion_mrr
    FROM mart.mrr_movements
    GROUP BY 1
)
SELECT
    month_start,
    opening_mrr,
    1 - coalesce(lost_mrr, 0) / nullif(opening_mrr, 0) AS gross_revenue_retention,
    (opening_mrr - coalesce(lost_mrr, 0) + coalesce(expansion_mrr, 0)) / nullif(opening_mrr, 0) AS net_revenue_retention
FROM movement;

CREATE OR REPLACE VIEW analytics.logo_churn AS
SELECT
    month_start,
    count(*) FILTER (WHERE previous_mrr > 0) AS opening_accounts,
    count(*) FILTER (WHERE movement_type = 'churn') AS churned_accounts,
    count(*) FILTER (WHERE movement_type = 'new') AS new_accounts,
    count(*) FILTER (WHERE movement_type = 'reactivation') AS reactivated_accounts,
    count(*) FILTER (WHERE movement_type = 'churn')::numeric /
        nullif(count(*) FILTER (WHERE previous_mrr > 0), 0) AS logo_churn_rate
FROM mart.mrr_movements
GROUP BY 1;

CREATE OR REPLACE VIEW analytics.add_on_attachment AS
SELECT
    month_start,
    segment,
    primary_plan_name,
    count(*) FILTER (WHERE mrr_eur > 0) AS active_accounts,
    count(*) FILTER (WHERE active_add_ons > 0 AND mrr_eur > 0) AS accounts_with_add_ons,
    avg(active_add_ons) FILTER (WHERE mrr_eur > 0) AS average_add_ons,
    count(*) FILTER (WHERE active_add_ons > 0 AND mrr_eur > 0)::numeric /
        nullif(count(*) FILTER (WHERE mrr_eur > 0), 0) AS attachment_rate
FROM mart.account_month
GROUP BY 1,2,3;

CREATE OR REPLACE VIEW analytics.revenue_concentration AS
WITH latest AS (
    SELECT max(month_start) AS month_start FROM mart.account_month
), ranked AS (
    SELECT
        am.account_id,
        am.mrr_eur,
        sum(am.mrr_eur) OVER () AS total_mrr,
        row_number() OVER (ORDER BY am.mrr_eur DESC) AS revenue_rank,
        count(*) OVER () AS account_count
    FROM mart.account_month am
    JOIN latest l USING (month_start)
    WHERE am.mrr_eur > 0
)
SELECT
    sum(mrr_eur) FILTER (WHERE revenue_rank <= greatest(1, ceil(account_count * 0.01))) / max(total_mrr) AS top_1_pct_share,
    sum(mrr_eur) FILTER (WHERE revenue_rank <= greatest(1, ceil(account_count * 0.10))) / max(total_mrr) AS top_10_pct_share,
    max(total_mrr) AS total_mrr
FROM ranked;
