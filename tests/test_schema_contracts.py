from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from b2b_saas_platform_analytics.schema import TABLE_SCHEMAS

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("table_name", sorted(TABLE_SCHEMAS))
def test_contract_matches_schema_registry(table_name):
    schema = TABLE_SCHEMAS[table_name]
    contract = yaml.safe_load(
        (ROOT / "contracts" / f"{table_name}.yaml").read_text(encoding="utf-8")
    )
    assert contract["table"] == table_name
    assert contract["primary_key"] == schema.get("primary_key", [])
    assert contract["foreign_keys"] == schema.get("foreign_keys", [])
    contract_columns = {column["name"]: column["type"] for column in contract["columns"]}
    assert contract_columns == schema["columns"]


@pytest.mark.parametrize("table_name", sorted(TABLE_SCHEMAS))
def test_generated_table_matches_governed_schema(table_name, generated_dataset):
    frame = generated_dataset.tables[table_name]
    schema = TABLE_SCHEMAS[table_name]
    assert list(frame.columns) == list(schema["columns"])
    primary_key = schema.get("primary_key", [])
    if primary_key:
        assert not frame[primary_key].isna().any().any()
        assert not frame.duplicated(primary_key).any()


FOREIGN_KEYS = [
    (table_name, foreign_key)
    for table_name, schema in TABLE_SCHEMAS.items()
    for foreign_key in schema.get("foreign_keys", [])
]


@pytest.mark.parametrize(
    ("table_name", "foreign_key"),
    FOREIGN_KEYS,
    ids=lambda value: str(value)[:70],
)
def test_generated_foreign_keys_resolve(table_name, foreign_key, generated_dataset):
    local_columns = foreign_key["columns"]
    reference = foreign_key["references"]
    reference_table, reference_columns_text = reference[:-1].split("(", 1)
    reference_columns = [column.strip() for column in reference_columns_text.split(",")]

    child = generated_dataset.tables[table_name][local_columns].dropna().drop_duplicates()
    parent = generated_dataset.tables[reference_table][reference_columns].drop_duplicates()
    child_keys = set(map(tuple, child.itertuples(index=False, name=None)))
    parent_keys = set(map(tuple, parent.itertuples(index=False, name=None)))
    assert child_keys <= parent_keys
