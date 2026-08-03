from b2b_saas_platform_analytics.generator import generate_dataset
from b2b_saas_platform_analytics.utils import dataframe_fingerprint

def test_generation_is_reproducible(sample_config):
    first = generate_dataset(sample_config)
    second = generate_dataset(sample_config)
    for table_name in ["accounts", "subscriptions", "invoices", "account_usage_daily", "experiment_outcomes"]:
        assert dataframe_fingerprint(first.tables[table_name]) == dataframe_fingerprint(second.tables[table_name])
