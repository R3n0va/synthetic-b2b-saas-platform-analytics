from copy import deepcopy
from b2b_saas_platform_analytics.validation import validate_tables, validation_passed

def test_generated_dataset_passes_validation(generated_dataset):
    results = validate_tables(generated_dataset.tables)
    assert validation_passed(results), results.loc[~results["passed"]].to_string(index=False)

def test_duplicate_primary_key_is_detected(generated_dataset):
    tables = {name: frame.copy() for name, frame in generated_dataset.tables.items()}
    tables["accounts"] = __import__('pandas').concat([tables["accounts"], tables["accounts"].iloc[[0]]], ignore_index=True)
    results = validate_tables(tables)
    assert ((results["check_type"] == "primary_key") & (~results["passed"])).any()

def test_missing_foreign_key_is_detected(generated_dataset):
    tables = {name: frame.copy() for name, frame in generated_dataset.tables.items()}
    tables["subscriptions"].loc[tables["subscriptions"].index[0], "account_id"] = "missing_account"
    results = validate_tables(tables)
    assert ((results["check_type"] == "foreign_key") & (~results["passed"])).any()
