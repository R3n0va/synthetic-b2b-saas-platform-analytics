from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
METRIC_REGISTRY = yaml.safe_load(
    (ROOT / "metrics/metric_definitions.yaml").read_text(encoding="utf-8")
)["metrics"]
BUSINESS_CASES = yaml.safe_load(
    (ROOT / "analytics/business_case_catalog.yaml").read_text(encoding="utf-8")
)["business_cases"]
SQL_TEXT = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "sql").rglob("*.sql"))


def test_metric_ids_are_unique():
    identifiers = [metric["metric_id"] for metric in METRIC_REGISTRY]
    assert len(identifiers) == len(set(identifiers))


@pytest.mark.parametrize("metric", METRIC_REGISTRY, ids=lambda metric: metric["metric_id"])
def test_governed_metric_is_complete(metric):
    assert set(metric) >= {"metric_id", "name", "definition", "grain", "source", "owner", "status"}
    assert metric["status"] == "governed"
    assert metric["definition"].strip()
    assert metric["source"].strip()


def test_business_case_ids_are_unique():
    identifiers = [case["case_id"] for case in BUSINESS_CASES]
    assert len(identifiers) == len(set(identifiers))


@pytest.mark.parametrize("case", BUSINESS_CASES, ids=lambda case: case["case_id"])
def test_business_case_maps_to_implemented_view(case):
    assert set(case) >= {"case_id", "domain", "question", "sql_view", "decision"}
    pattern = re.compile(
        rf"CREATE\s+OR\s+REPLACE\s+VIEW\s+{re.escape(case['sql_view'])}\b",
        re.IGNORECASE,
    )
    assert pattern.search(SQL_TEXT), case["sql_view"]
