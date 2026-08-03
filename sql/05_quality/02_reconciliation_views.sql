CREATE OR REPLACE VIEW quality.mrr_bridge_reconciliation AS
SELECT
    month_start,
    opening_mrr,
    coalesce(new_mrr, 0) AS new_mrr,
    coalesce(expansion_mrr, 0) AS expansion_mrr,
    coalesce(contraction_mrr, 0) AS contraction_mrr,
    coalesce(churned_mrr, 0) AS churned_mrr,
    coalesce(reactivation_mrr, 0) AS reactivation_mrr,
    closing_mrr,
    closing_mrr - (
        opening_mrr + coalesce(new_mrr, 0) + coalesce(expansion_mrr, 0)
        + coalesce(contraction_mrr, 0) + coalesce(churned_mrr, 0) + coalesce(reactivation_mrr, 0)
    ) AS reconciliation_difference
FROM analytics.monthly_mrr_bridge;

CREATE OR REPLACE VIEW quality.invoice_payment_reconciliation AS
SELECT
    i.invoice_id,
    i.total_eur,
    coalesce(sum(p.amount_eur), 0) AS captured_eur,
    coalesce(sum(r.amount_eur), 0) AS refunded_eur,
    i.total_eur - coalesce(sum(p.amount_eur), 0) AS unpaid_difference_eur,
    i.invoice_status
FROM core.invoices i
LEFT JOIN core.payments p USING (invoice_id)
LEFT JOIN core.refunds r USING (payment_id)
GROUP BY 1,2,6;

CREATE OR REPLACE VIEW quality.subscription_item_overlap AS
SELECT
    a.subscription_item_id AS left_item_id,
    b.subscription_item_id AS right_item_id,
    a.subscription_id,
    a.item_type,
    a.effective_start AS left_start,
    a.effective_end AS left_end,
    b.effective_start AS right_start,
    b.effective_end AS right_end
FROM core.subscription_items a
JOIN core.subscription_items b
  ON a.subscription_id = b.subscription_id
 AND a.item_type = b.item_type
 AND coalesce(a.plan_id, a.add_on_id) = coalesce(b.plan_id, b.add_on_id)
 AND a.subscription_item_id < b.subscription_item_id
 AND daterange(a.effective_start, a.effective_end, '[]') && daterange(b.effective_start, b.effective_end, '[]');
