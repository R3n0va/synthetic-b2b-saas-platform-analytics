CREATE OR REPLACE VIEW analytics.sales_funnel AS
SELECT
    country_code,
    region_id,
    sales_motion,
    acquisition_channel,
    count(DISTINCT account_id) AS accounts,
    count(DISTINCT lead_id) AS leads,
    count(DISTINCT account_id) FILTER (WHERE reached_mql) AS mqls,
    count(DISTINCT account_id) FILTER (WHERE reached_sql) AS sqls,
    count(DISTINCT opportunity_id) AS opportunities,
    count(DISTINCT opportunity_id) FILTER (WHERE opportunity_status = 'won') AS won_opportunities,
    count(DISTINCT account_id) FILTER (WHERE became_customer) AS paid_accounts,
    count(DISTINCT account_id) FILTER (WHERE became_customer)::numeric / nullif(count(DISTINCT account_id), 0) AS account_to_paid_rate
FROM mart.sales_funnel_account
GROUP BY 1,2,3,4;

CREATE OR REPLACE VIEW analytics.opportunity_win_rate AS
SELECT
    a.region_id,
    a.country_code,
    a.segment,
    a.sales_motion,
    count(*) AS opportunities,
    count(*) FILTER (WHERE o.status = 'won') AS won,
    count(*) FILTER (WHERE o.status = 'won')::numeric / nullif(count(*), 0) AS win_rate,
    avg(o.expected_arr_eur) AS average_expected_arr
FROM core.opportunities o
JOIN core.accounts a USING (account_id)
GROUP BY 1,2,3,4;

CREATE OR REPLACE VIEW analytics.sales_cycle AS
SELECT
    a.region_id,
    a.country_code,
    a.segment,
    a.sales_motion,
    o.status,
    avg(o.close_date - o.created_at::date) AS average_sales_cycle_days,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY o.close_date - o.created_at::date) AS median_sales_cycle_days
FROM core.opportunities o
JOIN core.accounts a USING (account_id)
GROUP BY 1,2,3,4,5;

CREATE OR REPLACE VIEW analytics.partner_performance AS
SELECT
    p.partner_id,
    p.partner_name,
    p.partner_type,
    p.country_code,
    count(DISTINCT a.account_id) AS referred_accounts,
    count(DISTINCT s.account_id) AS converted_accounts,
    count(DISTINCT s.account_id)::numeric / nullif(count(DISTINCT a.account_id), 0) AS conversion_rate,
    sum(am.mrr_eur) FILTER (WHERE am.month_start = (SELECT max(month_start) FROM mart.account_month)) AS current_mrr_eur
FROM core.partners p
LEFT JOIN core.accounts a USING (partner_id)
LEFT JOIN core.subscriptions s USING (account_id)
LEFT JOIN mart.account_month am USING (account_id)
GROUP BY 1,2,3,4;

CREATE OR REPLACE VIEW analytics.trial_conversion AS
SELECT
    a.country_code,
    a.segment,
    a.acquisition_channel,
    count(*) FILTER (WHERE s.trial_start_date IS NOT NULL) AS paid_after_trial,
    avg(s.subscription_start_date - s.trial_start_date) FILTER (WHERE s.trial_start_date IS NOT NULL) AS average_trial_days
FROM core.subscriptions s
JOIN core.accounts a USING (account_id)
GROUP BY 1,2,3;

CREATE OR REPLACE VIEW analytics.contract_mix AS
SELECT
    date_trunc('month', c.start_date)::date AS contract_month,
    a.region_id,
    a.segment,
    c.billing_frequency,
    c.contract_term_months,
    count(*) AS contracts,
    avg(c.discount_pct) AS average_discount,
    count(*) FILTER (WHERE c.auto_renew_flag)::numeric / nullif(count(*), 0) AS auto_renew_share
FROM core.contracts c
JOIN core.accounts a USING (account_id)
GROUP BY 1,2,3,4,5;

CREATE OR REPLACE VIEW analytics.marketing_efficiency AS
WITH acquired AS (
    SELECT
        date_trunc('month', s.subscription_start_date)::date AS month_start,
        a.country_code,
        a.acquisition_channel AS channel,
        count(DISTINCT s.account_id) AS acquired_accounts
    FROM core.subscriptions s
    JOIN core.accounts a USING (account_id)
    GROUP BY 1,2,3
), spend AS (
    SELECT date_trunc('month', start_date)::date AS month_start, country_code, channel, sum(spend_eur) AS spend_eur
    FROM core.marketing_campaigns
    GROUP BY 1,2,3
)
SELECT
    s.month_start,
    s.country_code,
    s.channel,
    s.spend_eur,
    coalesce(a.acquired_accounts, 0) AS acquired_accounts,
    s.spend_eur / nullif(a.acquired_accounts, 0) AS cac_eur
FROM spend s
LEFT JOIN acquired a USING (month_start, country_code, channel);
