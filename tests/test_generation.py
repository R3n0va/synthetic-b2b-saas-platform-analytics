from __future__ import annotations

import re

import pandas as pd
import pytest

from b2b_saas_platform_analytics.generator import (
    _prepare_frame_for_csv,
    write_dataset,
)
from b2b_saas_platform_analytics.schema import TABLE_SCHEMAS

def test_all_governed_tables_are_generated(generated_dataset):
    assert set(generated_dataset.tables) == set(TABLE_SCHEMAS)

def test_primary_business_entities_are_non_empty(generated_dataset):
    for table in ["accounts", "subscriptions", "subscription_items", "invoices", "payments", "account_usage_daily"]:
        assert not generated_dataset.tables[table].empty

def test_invoice_values_are_non_negative(generated_dataset):
    invoices = generated_dataset.tables["invoices"]
    assert (invoices["total_eur"].astype(float) >= 0).all()

def test_subscription_items_have_positive_mrr(generated_dataset):
    items = generated_dataset.tables["subscription_items"]
    assert (items["mrr_eur"].astype(float) > 0).all()

def test_csv_writer_serialises_governed_integer_columns_without_decimal_suffix(
    generated_dataset, tmp_path
):
    write_dataset(generated_dataset, tmp_path)
    integer_pattern = re.compile(r"^[+-]?\d+$")
    for table_name, schema in TABLE_SCHEMAS.items():
        integer_columns = [
            column for column, logical_type in schema["columns"].items()
            if logical_type == "integer"
        ]
        if not integer_columns:
            continue
        frame = pd.read_csv(
            tmp_path / f"{table_name}.csv",
            dtype=str,
            keep_default_na=False,
        )
        for column in integer_columns:
            values = frame.loc[frame[column] != "", column]
            assert values.map(lambda value: bool(integer_pattern.fullmatch(value))).all(), (
                table_name,
                column,
                values[~values.map(lambda value: bool(integer_pattern.fullmatch(value)))].head().tolist(),
            )


def test_csv_integer_normalisation_rejects_fractional_values():
    frame = pd.DataFrame({"minor_units": [2.5]})
    with pytest.raises(ValueError, match="non-integral value"):
        _prepare_frame_for_csv("currencies", frame)
