import pytest
from b2b_saas_platform_analytics.analytics import build_mrr_snapshot, build_mrr_bridge, build_retention, build_payment_recovery, build_experiment_decisions

def test_mrr_bridge_reconciles(generated_dataset, sample_config):
    snapshot = build_mrr_snapshot(generated_dataset.tables, sample_config)
    bridge, _ = build_mrr_bridge(snapshot, sample_config)
    identity = bridge["opening_mrr"] + bridge["new_mrr"] + bridge["expansion_mrr"] + bridge["contraction_mrr"] + bridge["churned_mrr"] + bridge["reactivation_mrr"]
    assert (identity - bridge["closing_mrr"]).abs().max() < 0.01

def test_retention_metrics_are_bounded(generated_dataset, sample_config):
    snapshot = build_mrr_snapshot(generated_dataset.tables, sample_config)
    _, retention = build_retention(snapshot)
    assert retention["gross_revenue_retention"].dropna().between(0, 1).all()
    assert (retention["net_revenue_retention"].dropna() >= 0).all()

def test_payment_recovery_is_bounded(generated_dataset):
    result = build_payment_recovery(generated_dataset.tables)
    assert result["recovery_rate"].dropna().between(0, 1).all()

def test_experiment_decisions_use_supported_labels(generated_dataset):
    result = build_experiment_decisions(generated_dataset.tables)
    assert set(result["decision"]).issubset({"LAUNCH", "DO NOT LAUNCH", "INCONCLUSIVE"})
