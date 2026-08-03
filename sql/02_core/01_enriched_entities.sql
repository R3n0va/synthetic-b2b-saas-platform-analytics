CREATE OR REPLACE VIEW core.v_accounts_enriched AS
SELECT
    a.*,
    c.country_name,
    c.currency_code AS country_currency,
    c.vat_rate,
    r.region_name
FROM core.accounts a
JOIN core.countries c
  ON c.country_code = a.country_code
JOIN core.regions r
  ON r.region_id = a.region_id;

CREATE OR REPLACE VIEW core.v_subscriptions_enriched AS
SELECT
    s.*,
    a.country_code,
    a.region_id,
    a.segment,
    a.sales_motion,
    a.acquisition_channel,
    p.plan_name,
    p.plan_rank,
    c.discount_pct AS contract_discount_pct,
    c.contract_term_months,
    c.auto_renew_flag
FROM core.subscriptions s
JOIN core.accounts a
  ON a.account_id = s.account_id
JOIN core.plans p
  ON p.plan_id = s.plan_id
JOIN core.contracts c
  ON c.contract_id = s.contract_id
 AND c.account_id = s.account_id;

CREATE OR REPLACE VIEW core.v_subscription_items_enriched AS
SELECT
    si.*,
    s.account_id,
    s.currency_code,
    p.plan_name,
    ao.add_on_name
FROM core.subscription_items si
JOIN core.subscriptions s
  ON s.subscription_id = si.subscription_id
LEFT JOIN core.plans p
  ON p.plan_id = si.plan_id
LEFT JOIN core.add_ons ao
  ON ao.add_on_id = si.add_on_id;

CREATE OR REPLACE VIEW core.v_invoices_enriched AS
SELECT
    i.*,
    a.country_code,
    a.region_id,
    a.segment,
    a.sales_motion,
    s.billing_frequency,
    s.plan_id
FROM core.invoices i
JOIN core.accounts a
  ON a.account_id = i.account_id
JOIN core.subscriptions s
  ON s.subscription_id = i.subscription_id
 AND s.account_id = i.account_id;
